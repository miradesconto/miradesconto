#!/usr/bin/env python3
"""Diagnostica quais campos de preço o catálogo do Mercado Livre expõe ao MiraDesconto."""
from __future__ import annotations

import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import sync_catalog as base

CATEGORY_ID = "MLB432825"


def request_json(url: str, token: str):
    req = Request(url, headers={
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "MiraDesconto/1.0 (+https://miradesconto.github.io/miradesconto/)",
    }, method="GET")
    try:
        with urlopen(req, timeout=45) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(raw)
        except Exception:
            return exc.code, {"raw": raw[:200]}


def main() -> int:
    token, mode = base.get_access_token()
    print("AUTH_MODE=" + mode)
    status, highlights = request_json(f"{base.API_BASE}/highlights/MLB/category/{CATEGORY_ID}", token)
    rows = highlights.get("content", []) if status == 200 and isinstance(highlights, dict) else []
    product_ids = [str(r.get("id")) for r in rows if isinstance(r, dict) and r.get("type") == "PRODUCT" and r.get("id")][:20]
    stats = {"requested": len(product_ids), "http_200": 0, "active": 0, "winner": 0, "winner_price": 0, "price_like_top_level": 0}
    samples = []
    for pid in product_ids:
        s, product = request_json(f"{base.API_BASE}/products/{pid}", token)
        sample = {"product_id": pid, "http": s}
        if s == 200 and isinstance(product, dict):
            stats["http_200"] += 1
            if product.get("status") == "active": stats["active"] += 1
            winner = product.get("buy_box_winner")
            if isinstance(winner, dict):
                stats["winner"] += 1
                if isinstance(winner.get("price"), (int, float)): stats["winner_price"] += 1
            top_price_keys = [k for k in product.keys() if "price" in k.lower() or "offer" in k.lower() or "buy" in k.lower()]
            if top_price_keys: stats["price_like_top_level"] += 1
            sample.update({
                "status": product.get("status"),
                "keys": sorted(product.keys()),
                "price_like_keys": top_price_keys,
                "winner_type": type(winner).__name__,
                "winner_keys": sorted(winner.keys()) if isinstance(winner, dict) else [],
                "winner_has_price": isinstance(winner, dict) and isinstance(winner.get("price"), (int, float)),
                "catalog_listing": product.get("catalog_listing"),
                "type": product.get("type"),
            })
        samples.append(sample)
    print("PRODUCT_PRICE_STATS=" + json.dumps(stats, ensure_ascii=False))
    print("PRODUCT_SAMPLES=" + json.dumps(samples[:5], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
