#!/usr/bin/env python3
"""Diagnostica campos de preço expostos por /products/search no Mercado Livre."""
from __future__ import annotations

import json
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

import sync_catalog as base

QUERIES = [
    "Samsung",
    "Lixeira Inteligente Automatica Cinza Universal Sensor Recarregavel 16l",
    "Kit 4 camiseta dry fit masculina academia caminhada",
]


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


def compact(row):
    if not isinstance(row, dict):
        return {"type": type(row).__name__}
    price_keys = [k for k in row if any(word in k.lower() for word in ("price", "offer", "buy", "seller"))]
    winner = row.get("buy_box_winner")
    return {
        "id": row.get("id"),
        "name": row.get("name") or row.get("family_name"),
        "keys": sorted(row.keys()),
        "price_like_keys": price_keys,
        "price": row.get("price"),
        "original_price": row.get("original_price"),
        "winner_type": type(winner).__name__,
        "winner": {k: winner.get(k) for k in ("item_id", "price", "original_price", "currency_id", "available_quantity") if k in winner} if isinstance(winner, dict) else None,
    }


def main() -> int:
    token, mode = base.get_access_token()
    print("AUTH_MODE=" + mode)
    for query in QUERIES:
        status, payload = request_json(
            f"{base.API_BASE}/products/search?status=active&site_id=MLB&q={quote(query)}",
            token,
        )
        results = payload.get("results", []) if status == 200 and isinstance(payload, dict) else []
        print("SEARCH=" + json.dumps({
            "query": query,
            "http": status,
            "total": payload.get("paging", {}).get("total") if isinstance(payload, dict) else None,
            "result_count": len(results) if isinstance(results, list) else 0,
            "samples": [compact(r) for r in results[:5]] if isinstance(results, list) else [],
        }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
