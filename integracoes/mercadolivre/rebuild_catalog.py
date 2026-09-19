#!/usr/bin/env python3
"""Reconstrói o catálogo MiraDesconto com dados atuais da API do Mercado Livre.

Regras de segurança:
- mantém somente links de afiliado já gerados oficialmente para a conta MiraDesconto;
- confirma que cada link curto ainda contém como destino o anúncio original;
- associa o anúncio ao catálogo atual por Product ID direto ou por título com
  similaridade alta;
- valida produto, disponibilidade e preço atual em /products/{product_id};
- não inventa parâmetros de afiliado nem cria tracking manualmente.
"""
from __future__ import annotations

import argparse
import difflib
import html
import json
import re
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import sync_catalog as base

PRODUCT_ID_RE = re.compile(r"/p/(MLB\d+)(?:[/?#]|$)", re.I)
MAX_WORKERS = 10
SEARCH_LIMIT = 700
BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/153 Safari/537.36"


def get_json(url: str, token: str, attempts: int = 4) -> Any:
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "MiraDesconto/1.0 (+https://miradesconto.github.io/miradesconto/)",
    }
    for attempt in range(1, attempts + 1):
        req = Request(url, headers=headers, method="GET")
        try:
            with urlopen(req, timeout=40) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code in {429, 500, 502, 503, 504} and attempt < attempts:
                time.sleep(min(2 ** attempt, 8))
                continue
            return None
        except (URLError, TimeoutError, json.JSONDecodeError):
            if attempt < attempts:
                time.sleep(min(2 ** attempt, 8))
                continue
            return None
    return None


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.lower())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def title_similarity(a: str, b: str) -> float:
    na, nb = normalize_text(a), normalize_text(b)
    if not na or not nb:
        return 0.0
    seq = difflib.SequenceMatcher(None, na, nb).ratio()
    ta, tb = set(na.split()), set(nb.split())
    union = ta | tb
    jaccard = len(ta & tb) / len(union) if union else 0.0
    containment = len(ta & tb) / max(1, min(len(ta), len(tb)))
    return max(seq, 0.55 * jaccard + 0.45 * containment)


def resolve_affiliate_target(affiliate_url: str, expected_item_id: str) -> dict[str, Any] | None:
    """Resolve meli.la e confirma o anúncio original dentro da página /social/.

    Os links atuais do programa podem terminar numa página /social/... que contém
    o URL real do anúncio no HTML. Por isso não basta observar response.geturl().
    """
    if not affiliate_url.startswith("https://"):
        return None
    expected_item_id = expected_item_id.upper().replace("-", "").strip()
    req = Request(
        affiliate_url,
        headers={"Accept": "text/html,application/xhtml+xml", "User-Agent": BROWSER_UA},
        method="GET",
    )
    try:
        with urlopen(req, timeout=30) as response:
            final_url = response.geturl()
            body = response.read(900_000).decode("utf-8", errors="replace")
        decoded = html.unescape(body).replace("\\u002F", "/").replace("\\/", "/")

        direct_product = PRODUCT_ID_RE.search(final_url)
        if direct_product:
            return {"product_id": direct_product.group(1).upper(), "item_id": None}

        # A página social contém recomendações adicionais. Só aceitamos como
        # destino o mesmo item que já estava registrado no nosso catálogo.
        if expected_item_id.startswith("MLB"):
            digits = re.escape(expected_item_id[3:])
            if re.search(rf"MLB-?{digits}(?:[-_/?#&\"']|$)", decoded, flags=re.I):
                return {"product_id": None, "item_id": expected_item_id}

        # Fallback apenas para um Product ID explícito no destino principal.
        product_urls = re.findall(r"https?://[^\"'<>\\\s]+/p/(MLB\d+)(?:[/?#]|$)", decoded, flags=re.I)
        if len(set(p.upper() for p in product_urls)) == 1:
            return {"product_id": product_urls[0].upper(), "item_id": None}
        return None
    except Exception:
        return None


def resolve_targets(products: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], int, int]:
    pairs = []
    for product in products:
        url = str(product.get("affiliateUrl") or "").strip()
        item_id = str(product.get("id") or "").strip()
        if url and item_id:
            pairs.append((url, item_id, product))

    viable: list[dict[str, Any]] = []
    direct: dict[str, dict[str, Any]] = {}
    resolved = direct_count = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(resolve_affiliate_target, url, item_id): product
            for url, item_id, product in pairs
        }
        for future in as_completed(futures):
            product = futures[future]
            try:
                target = future.result()
            except Exception:
                target = None
            if not target:
                continue
            resolved += 1
            product_id = target.get("product_id")
            if product_id:
                direct_count += 1
                current = direct.get(product_id)
                if current is None or int(product.get("rank") or 999999) < int(current.get("rank") or 999999):
                    direct[product_id] = product
            else:
                viable.append(product)

    viable.sort(key=lambda p: int(p.get("rank") or 999999))
    return viable, direct, resolved, direct_count


def search_catalog_product(old: dict[str, Any], token: str) -> tuple[str, float] | None:
    title = str(old.get("name") or "").strip()
    if not title:
        return None
    query = quote(title[:180])
    payload = get_json(f"{base.API_BASE}/products/search?status=active&site_id=MLB&q={query}", token)
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        return None

    best_id = None
    best_score = 0.0
    for row in payload["results"][:10]:
        if not isinstance(row, dict) or not row.get("id"):
            continue
        candidate_name = str(row.get("name") or row.get("family_name") or "")
        score = title_similarity(title, candidate_name)
        if score > best_score:
            best_score = score
            best_id = str(row["id"]).upper()
    if best_id and best_score >= 0.72:
        return best_id, round(best_score, 4)
    return None


def build_affiliate_map(products: list[dict[str, Any]], token: str) -> tuple[dict[str, dict[str, Any]], dict[str, int]]:
    viable, direct, resolved, direct_count = resolve_targets(products)
    mapping = dict(direct)
    title_matches = 0
    candidates = viable[:SEARCH_LIMIT]

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(search_catalog_product, product, token): product for product in candidates}
        for future in as_completed(futures):
            old = futures[future]
            try:
                match = future.result()
            except Exception:
                match = None
            if not match:
                continue
            product_id, score = match
            title_matches += 1
            old = dict(old)
            old["catalogMatchScore"] = score
            current = mapping.get(product_id)
            if current is None or int(old.get("rank") or 999999) < int(current.get("rank") or 999999):
                mapping[product_id] = old

    stats = {
        "affiliate_targets_resolved": resolved,
        "direct_catalog_ids": direct_count,
        "title_search_candidates": len(candidates),
        "title_matches": title_matches,
        "catalog_product_ids_mapped": len(mapping),
    }
    return mapping, stats


def fetch_highlight_ranks(token: str) -> tuple[dict[str, tuple[int, int, str]], int]:
    categories = get_json(f"{base.API_BASE}/sites/MLB/categories", token)
    if not isinstance(categories, list):
        return {}, 0

    top_categories = [c for c in categories if isinstance(c, dict) and c.get("id") and c.get("name")]
    ranks: dict[str, tuple[int, int, str]] = {}

    def fetch_category(index_category):
        index, category = index_category
        payload = get_json(f"{base.API_BASE}/highlights/MLB/category/{category['id']}", token)
        return index, category, payload

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(fetch_category, pair) for pair in enumerate(top_categories)]
        for future in as_completed(futures):
            try:
                category_index, category, payload = future.result()
            except Exception:
                continue
            if not isinstance(payload, dict):
                continue
            content = payload.get("content")
            if not isinstance(content, list):
                continue
            position = 0
            for row in content:
                if not isinstance(row, dict) or row.get("type") != "PRODUCT" or not row.get("id"):
                    continue
                position += 1
                pid = str(row["id"]).upper()
                score = (category_index, position, str(category["name"]))
                if pid not in ranks or score[:2] < ranks[pid][:2]:
                    ranks[pid] = score
    return ranks, len(top_categories)


def fetch_product_detail(product_id: str, token: str) -> dict[str, Any] | None:
    payload = get_json(f"{base.API_BASE}/products/{product_id}", token)
    return payload if isinstance(payload, dict) else None


def image_from_detail(detail: dict[str, Any], fallback: str | None) -> str | None:
    pictures = detail.get("pictures")
    if isinstance(pictures, list) and pictures:
        pic = pictures[0]
        if isinstance(pic, dict):
            for key in ("secure_url", "url", "thumbnail"):
                value = pic.get(key)
                if isinstance(value, str) and value.startswith("http"):
                    return value
            pic_id = pic.get("id")
            if isinstance(pic_id, str) and pic_id:
                return f"https://http2.mlstatic.com/D_NQ_NP_2X_{pic_id}-O.webp"
    return fallback


def valid_price(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool) and float(value) > 0:
        return round(float(value), 2)
    return None


def build_product(product_id: str, old: dict[str, Any], detail: dict[str, Any],
                  highlight: tuple[int, int, str] | None, collected_at: str) -> dict[str, Any] | None:
    if str(detail.get("status") or "").lower() != "active":
        return None
    winner = detail.get("buy_box_winner")
    if not isinstance(winner, dict):
        return None
    price = valid_price(winner.get("price"))
    if price is None:
        return None

    original = valid_price(winner.get("original_price"))
    old_price = original if original is not None and original > price else None
    discount = round((1 - price / old_price) * 100, 4) if old_price else None

    category = highlight[2] if highlight else str(old.get("category") or "Ofertas")
    name = str(detail.get("name") or old.get("name") or "").strip()
    affiliate_url = str(old.get("affiliateUrl") or "").strip()
    if not name or not affiliate_url:
        return None

    result = {
        "id": product_id,
        "catalogProductId": product_id,
        "itemId": winner.get("item_id"),
        "name": name,
        "category": category,
        "price": price,
        "oldPrice": old_price,
        "discount": discount,
        "displayedDiscount": f"{round(discount)}% OFF" if discount else None,
        "affiliateUrl": affiliate_url,
        "imageUrl": image_from_detail(detail, old.get("imageUrl")),
        "productUrl": detail.get("permalink") or None,
        "featured": False,
        "available": True,
        "collectedAt": collected_at,
        "source": "Mercado Livre API",
        "affiliateLinkSource": "official_existing",
        "previousRank": old.get("rank"),
    }
    if old.get("catalogMatchScore") is not None:
        result["catalogMatchScore"] = old.get("catalogMatchScore")
    return result


def fresh_data_json(products: list[dict[str, Any]]) -> None:
    payload: dict[str, Any] = {}
    for product in products:
        payload[str(product["id"])] = {
            "name": product.get("name"),
            "imageUrl": product.get("imageUrl"),
            "available": True,
        }
    base.DATA_PRODUTOS.parent.mkdir(parents=True, exist_ok=True)
    base.DATA_PRODUTOS.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-products", type=int, default=500)
    parser.add_argument("--min-products", type=int, default=40)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    old_data = base.load_mira_data()
    old_products = [p for p in old_data.get("products", []) if isinstance(p, dict)]
    if not old_products:
        raise RuntimeError("Catálogo anterior vazio; não há links oficiais para preservar.")

    token, auth_mode = base.get_access_token()

    affiliate_map, map_stats = build_affiliate_map(old_products, token)
    print(json.dumps({"old_products": len(old_products), **map_stats}, ensure_ascii=False))
    if not affiliate_map:
        raise RuntimeError("Nenhum link oficial pôde ser associado com segurança ao catálogo atual.")

    highlight_ranks, category_count = fetch_highlight_ranks(token)
    print(json.dumps({"highlight_categories": category_count, "highlight_products": len(highlight_ranks)}))

    details: dict[str, dict[str, Any]] = {}
    ids = list(affiliate_map.keys())
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(fetch_product_detail, pid, token): pid for pid in ids}
        for future in as_completed(futures):
            pid = futures[future]
            try:
                detail = future.result()
            except Exception:
                detail = None
            if detail:
                details[pid] = detail

    timestamp = base.now_sp()
    collected_at = timestamp.strftime("%d/%m/%Y")
    rebuilt: list[dict[str, Any]] = []
    for pid, old in affiliate_map.items():
        detail = details.get(pid)
        if not detail:
            continue
        built = build_product(pid, old, detail, highlight_ranks.get(pid), collected_at)
        if built:
            rebuilt.append(built)

    def sort_key(product: dict[str, Any]):
        pid = str(product["id"])
        highlight = highlight_ranks.get(pid)
        if highlight:
            return (0, highlight[0], highlight[1], int(product.get("previousRank") or 999999))
        return (1, 999999, 999999, int(product.get("previousRank") or 999999))

    rebuilt.sort(key=sort_key)
    if args.max_products > 0:
        rebuilt = rebuilt[:args.max_products]

    for rank, product in enumerate(rebuilt, start=1):
        product["rank"] = rank
        product["featured"] = rank <= 12
        product.pop("previousRank", None)

    highlighted_matches = sum(1 for p in rebuilt if str(p["id"]) in highlight_ranks)
    summary = {
        "old_products": len(old_products),
        **map_stats,
        "api_details_ok": len(details),
        "new_products": len(rebuilt),
        "highlighted_matches": highlighted_matches,
        "dry_run": bool(args.dry_run),
    }
    print(json.dumps(summary, ensure_ascii=False))

    if len(rebuilt) < args.min_products:
        raise RuntimeError(
            f"Reconstrução segura encontrou só {len(rebuilt)} produtos; mínimo configurado é {args.min_products}. "
            "Catálogo atual foi preservado."
        )
    if args.dry_run:
        return 0

    new_data = {
        "sourceFile": "Mercado Livre API + links oficiais MiraDesconto",
        "collectedAt": collected_at,
        "products": rebuilt,
        "apiSync": {
            "source": "Mercado Livre API",
            "updatedAt": timestamp.isoformat(timespec="seconds"),
            "strategy": "catalog-products-with-existing-official-affiliate-links",
            "endpoints": ["/products/search", "/products/{product_id}", "/highlights/MLB/category/{category_id}"],
        },
    }
    base.write_produtos_js(new_data)
    catalog_files = base.write_catalog_chunks(rebuilt)
    fresh_data_json(rebuilt)
    base.write_report({
        "updatedAt": timestamp.isoformat(timespec="seconds"),
        "source": "Mercado Livre API",
        "authentication": auth_mode,
        "strategy": "rebuild-current-catalog-preserving-official-affiliate-links",
        **summary,
        "catalogFiles": catalog_files,
    })
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERRO: {exc}")
        raise SystemExit(1)
