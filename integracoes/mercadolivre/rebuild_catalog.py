#!/usr/bin/env python3
"""Atualiza o catálogo MiraDesconto usando os links oficiais de afiliado já existentes.

A API pública de catálogo do Mercado Livre não expõe preço/buy-box para estes
produtos. Os links meli.la, porém, abrem páginas públicas oficiais do programa
de afiliados que contêm o anúncio original e o preço atual exibido. Este script:
- nunca cria nem altera parâmetros de afiliado;
- só aceita o item já registrado no catálogo;
- lê o preço atual da página pública oficial;
- descarta entradas sem confirmação suficiente;
- mantém uma trava para nunca substituir o catálogo por resultado anormalmente pequeno.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import sync_catalog as base

BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/153 Safari/537.36"
MAX_WORKERS = 10
MAX_BODY = 1_200_000


def normalize_item_id(value: Any) -> str:
    text = str(value or "").upper().replace("-", "").strip()
    return text if re.fullmatch(r"MLB\d{7,}", text) else ""


def valid_price(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if 0 < number < 10_000_000:
        return round(number, 2)
    return None


def fetch_affiliate_page(url: str, attempts: int = 3) -> tuple[str, str] | None:
    if not url.startswith("https://"):
        return None
    headers = {
        "Accept": "text/html,application/xhtml+xml",
        "User-Agent": BROWSER_UA,
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.7",
    }
    for attempt in range(1, attempts + 1):
        req = Request(url, headers=headers, method="GET")
        try:
            with urlopen(req, timeout=35) as response:
                body = response.read(MAX_BODY).decode("utf-8", errors="replace")
                return response.geturl(), html.unescape(body).replace("\\u002F", "/").replace("\\/", "/")
        except HTTPError as exc:
            if exc.code not in {429, 500, 502, 503, 504} or attempt == attempts:
                return None
        except (URLError, TimeoutError):
            if attempt == attempts:
                return None
        time.sleep(min(2 ** attempt, 6))
    return None


def item_occurrences(body: str, item_id: str) -> list[int]:
    digits = re.escape(item_id[3:])
    positions = [m.start() for m in re.finditer(rf"MLB-?{digits}", body, flags=re.I)]
    return positions[:20]


def numeric_candidates(chunk: str, labels: list[str], absolute_start: int) -> list[tuple[int, float, str]]:
    out: list[tuple[int, float, str]] = []
    for priority, label in enumerate(labels):
        patterns = [
            rf'"{label}"\s*:\s*([0-9]+(?:\.[0-9]+)?)',
            rf'"{label}"\s*:\s*\{{[^{{}}]{{0,900}}?"(?:value|amount|price)"\s*:\s*([0-9]+(?:\.[0-9]+)?)',
        ]
        for pattern in patterns:
            for m in re.finditer(pattern, chunk, flags=re.I | re.S):
                value = valid_price(m.group(1))
                if value is not None:
                    out.append((absolute_start + m.start() + priority * 25, value, label))
    return out


def nearest_price(body: str, item_id: str, labels: list[str]) -> tuple[float | None, str | None]:
    occurrences = item_occurrences(body, item_id)
    if not occurrences:
        return None, None
    candidates: list[tuple[int, int, float, str]] = []
    for pos in occurrences:
        start = max(0, pos - 3500)
        end = min(len(body), pos + 3500)
        chunk = body[start:end]
        for abs_pos, value, label in numeric_candidates(chunk, labels, start):
            candidates.append((labels.index(label), abs(abs_pos - pos), value, label))
    if not candidates:
        return None, None
    candidates.sort(key=lambda x: (x[0], x[1]))
    _, _, value, label = candidates[0]
    return value, label


def extract_product_url(body: str, item_id: str) -> str | None:
    digits = re.escape(item_id[3:])
    patterns = [
        rf'https?://[^\"\'<>\s]+/MLB-{digits}[^\"\'<>\s]*',
        rf'https?://[^\"\'<>\s]+MLB-?{digits}[^\"\'<>\s]*',
    ]
    for pattern in patterns:
        m = re.search(pattern, body, flags=re.I)
        if m:
            url = m.group(0)
            if "mercadolivre.com.br" in url:
                return url
    return None


def refresh_one(old: dict[str, Any], collected_at: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    item_id = normalize_item_id(old.get("id"))
    affiliate_url = str(old.get("affiliateUrl") or "").strip()
    if not item_id or not affiliate_url:
        return None, {"id": item_id or None, "reason": "missing_id_or_affiliate_url"}

    fetched = fetch_affiliate_page(affiliate_url)
    if not fetched:
        return None, {"id": item_id, "reason": "affiliate_page_unreachable"}
    _, body = fetched
    occurrences = item_occurrences(body, item_id)
    if not occurrences:
        return None, {"id": item_id, "reason": "original_item_not_found_in_affiliate_page"}

    price, price_source = nearest_price(body, item_id, ["current_price", "price"])
    if price is None:
        return None, {"id": item_id, "reason": "current_price_not_found"}

    previous, previous_source = nearest_price(
        body, item_id, ["previous_price", "original_price", "old_price"]
    )
    old_price = previous if previous is not None and previous > price else None
    discount = round((1 - price / old_price) * 100, 4) if old_price else None

    product_url = extract_product_url(body, item_id) or old.get("productUrl")
    result = dict(old)
    result.update({
        "id": item_id,
        "price": price,
        "oldPrice": old_price,
        "discount": discount,
        "displayedDiscount": f"{round(discount)}% OFF" if discount else None,
        "productUrl": product_url,
        "available": True,
        "collectedAt": collected_at,
        "source": "Mercado Livre — página pública de afiliados",
        "affiliateLinkSource": "official_existing",
        "priceSource": price_source,
    })
    if previous_source:
        result["previousPriceSource"] = previous_source
    return result, None


def write_data_products(products: list[dict[str, Any]]) -> None:
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
    data = base.load_mira_data()
    old_products = [p for p in data.get("products", []) if isinstance(p, dict)]
    if not old_products:
        raise RuntimeError("Catálogo anterior vazio; nada foi alterado.")

    old_products.sort(key=lambda p: int(p.get("rank") or 999999))
    scan_limit = len(old_products)
    if args.max_products > 0:
        scan_limit = min(len(old_products), max(args.max_products + 120, int(args.max_products * 1.35)))
    candidates = old_products[:scan_limit]

    timestamp = base.now_sp()
    collected_at = timestamp.strftime("%d/%m/%Y")
    refreshed: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(refresh_one, product, collected_at): product for product in candidates}
        done = 0
        for future in as_completed(futures):
            done += 1
            try:
                product, error = future.result()
            except Exception as exc:
                product, error = None, {"id": futures[future].get("id"), "reason": type(exc).__name__}
            if product:
                refreshed.append(product)
            elif error and len(errors) < 120:
                errors.append(error)
            if done % 50 == 0 or done == len(candidates):
                print(f"Progresso: {done}/{len(candidates)} links verificados; {len(refreshed)} preços atuais encontrados")

    refreshed.sort(key=lambda p: int(p.get("rank") or 999999))
    if args.max_products > 0:
        refreshed = refreshed[:args.max_products]
    for rank, product in enumerate(refreshed, start=1):
        product["rank"] = rank
        product["featured"] = rank <= 12

    summary = {
        "old_products": len(old_products),
        "links_checked": len(candidates),
        "current_prices_found": len(refreshed),
        "errors_sampled": len(errors),
        "dry_run": bool(args.dry_run),
    }
    print(json.dumps(summary, ensure_ascii=False))

    if len(refreshed) < args.min_products:
        raise RuntimeError(
            f"Só {len(refreshed)} produtos tiveram preço atual confirmado; mínimo de segurança é {args.min_products}. "
            "Catálogo anterior foi preservado."
        )
    if args.dry_run:
        return 0

    new_data = {
        "sourceFile": "Mercado Livre — páginas públicas oficiais de afiliados",
        "collectedAt": collected_at,
        "products": refreshed,
        "apiSync": {
            "source": "Mercado Livre — páginas públicas oficiais de afiliados",
            "updatedAt": timestamp.isoformat(timespec="seconds"),
            "strategy": "existing-official-affiliate-links-live-price",
            "linksChecked": len(candidates),
            "pricesConfirmed": len(refreshed),
        },
    }
    base.write_produtos_js(new_data)
    catalog_files = base.write_catalog_chunks(refreshed)
    write_data_products(refreshed)
    base.write_report({
        "updatedAt": timestamp.isoformat(timespec="seconds"),
        "source": "Mercado Livre — páginas públicas oficiais de afiliados",
        "strategy": "existing-official-affiliate-links-live-price",
        **summary,
        "catalogFiles": catalog_files,
        "errors": errors,
    })
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERRO: {exc}")
        raise SystemExit(1)
