#!/usr/bin/env python3
"""Atualiza somente preços associados a um cartão exato do produto.

Página sem estrutura reconhecida, variação divergente ou resultado ambíguo
é uma falha de confirmação, nunca motivo para escolher um preço próximo.
Encontrar um preço não comprova estoque.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from urllib.parse import urlsplit
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import sync_catalog as base
from product_card import extract, Unconfirmed

BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/153 Safari/537.36"
MAX_WORKERS = 10
MAX_BODY = 3_000_000


def normalize_item_id(value: Any) -> str:
    text = str(value or "").upper().replace("-", "").strip()
    return text if re.fullmatch(r"MLB\d{7,}", text) else ""


def fetch_affiliate_page(url: str, attempts: int = 3) -> tuple[str, str] | None:
    if not url.startswith("https://meli.la/"):
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
                host = urlsplit(response.geturl()).hostname or ""
                if not (host == "mercadolivre.com.br" or host.endswith(".mercadolivre.com.br")):
                    return None
                raw = response.read(MAX_BODY + 1)
                if len(raw) > MAX_BODY:
                    return None
                return response.geturl(), raw.decode("utf-8", errors="replace")
        except HTTPError as exc:
            if exc.code not in {429, 500, 502, 503, 504} or attempt == attempts:
                return None
        except (URLError, TimeoutError):
            if attempt == attempts:
                return None
        time.sleep(min(2 ** attempt, 6))
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
    reference_url = old.get("imageSource") or old.get("productUrl") or ""
    try:
        observation = extract(body, item_id, reference_url)
    except (Unconfirmed, ValueError) as exc:
        return None, {"id": item_id, "reason": str(exc)}
    price = observation["price"]
    previous = old.get("price")
    if isinstance(previous, (int, float)) and not isinstance(previous, bool) and previous > 0:
        if abs(price / previous - 1) > 0.5:
            return None, {"id": item_id, "reason": "price_jump_requires_review"}
    old_price = observation["oldPrice"]
    discount = round((1 - price / old_price) * 100, 4) if old_price else None
    checked = datetime.fromisoformat(collected_at)
    if checked.tzinfo is None:
        raise ValueError("checkedAt exige fuso horário")
    result = dict(old)
    for key in ("priceEvidence", "installment", "previousPriceSource"):
        result.pop(key, None)
    result.update({
        "price": price, "oldPrice": old_price, "discount": discount,
        "displayedDiscount": f"{round(discount)}% OFF" if discount else None,
        "available": None,
        "availabilityStatus": "unknown",
        "collectedAt": checked.strftime("%d/%m/%Y"),
        "source": "Mercado Livre — cartão público do produto",
        "affiliateLinkSource": "official_existing",
        "priceSource": "poly-card-v1",
        "priceCheck": {
            "status": "verified", "method": "poly-card-v1",
            "itemId": item_id, "variationId": observation["variationId"],
            "currency": "BRL", "checkedAt": checked.isoformat(timespec="seconds"),
            "price": price, "oldPrice": old_price,
        },
    })
    return result, None


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-products", type=int, default=500)
    parser.add_argument("--min-products", type=int, default=450)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv=None, source=None) -> int:
    args = parse_args(argv)
    data = source if source is not None else {"products": base.catalogo.load(base.ROOT)["products"]}
    old_products = [p for p in data.get("products", []) if isinstance(p, dict)]
    if not old_products:
        raise RuntimeError("Catálogo anterior vazio; nada foi alterado.")

    order = {p["id"]: i for i, p in enumerate(old_products)}
    scan_limit = len(old_products)
    if args.max_products > 0:
        scan_limit = min(len(old_products), max(args.max_products + 120, int(args.max_products * 1.35)))
    candidates = old_products[:scan_limit]

    timestamp = base.now_sp()
    collected_at = timestamp.strftime("%d/%m/%Y")
    refreshed: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    reasons = Counter()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(refresh_one, product, timestamp.isoformat(timespec="seconds")): product for product in candidates}
        done = 0
        for future in as_completed(futures):
            done += 1
            try:
                product, error = future.result()
            except Exception as exc:
                product, error = None, {"id": futures[future].get("id"), "reason": type(exc).__name__}
            if product:
                refreshed.append(product)
            elif error:
                reasons[error["reason"]] += 1
                if len(errors) < 120:
                    errors.append(error)
            if done % 50 == 0 or done == len(candidates):
                print(f"Progresso: {done}/{len(candidates)} links verificados; {len(refreshed)} preços atuais encontrados")

    refreshed.sort(key=lambda p: order[p["id"]])
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
        "failures": sum(reasons.values()),
        "failureReasons": dict(sorted(reasons.items())),
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
            "strategy": "exact-product-card-v1",
            "linksChecked": len(candidates),
            "pricesConfirmed": len(refreshed),
        },
    }
    base.catalogo.apply_snapshot(new_data, base.ROOT)
    catalog_files = (len(refreshed) + 99) // 100
    base.write_report({
        "updatedAt": timestamp.isoformat(timespec="seconds"),
        "source": "Mercado Livre — páginas públicas oficiais de afiliados",
        "strategy": "exact-product-card-v1",
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
