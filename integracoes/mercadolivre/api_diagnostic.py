#!/usr/bin/env python3
"""Diagnóstico mínimo da API do Mercado Livre sem expor credenciais."""
from __future__ import annotations

import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import sync_catalog as base

ITEM_ID = "MLB4592320910"


def call(label: str, url: str, token: str) -> None:
    req = Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "MiraDesconto/1.0 (+https://miradesconto.github.io/miradesconto/)",
        },
        method="GET",
    )
    try:
        with urlopen(req, timeout=45) as response:
            raw = response.read().decode("utf-8", errors="replace")
            print(f"\n=== {label} ===")
            print(f"HTTP={response.status}")
            try:
                payload = json.loads(raw)
                print(json.dumps(payload, ensure_ascii=False)[:4000])
            except Exception:
                print(raw[:4000])
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        print(f"\n=== {label} ===")
        print(f"HTTP={exc.code}")
        print(raw[:4000])


def main() -> int:
    token, auth_mode = base.get_access_token()
    print(f"AUTH_MODE={auth_mode}")

    calls = [
        ("USERS_ME", f"{base.API_BASE}/users/me"),
        ("ITEM_SINGLE_NO_ATTRIBUTES", f"{base.API_BASE}/items/{ITEM_ID}"),
        ("ITEM_SINGLE_WITH_ATTRIBUTES", f"{base.API_BASE}/items/{ITEM_ID}?attributes=id,title,status,permalink,price,original_price"),
        ("ITEM_BULK_NO_ATTRIBUTES", f"{base.API_BASE}/items/bulk?ids={ITEM_ID}"),
        ("ITEM_BULK_WITH_ATTRIBUTES", f"{base.API_BASE}/items/bulk?ids={ITEM_ID}&attributes=body.id,body.title,body.status,body.permalink,body.price,body.original_price"),
        ("ITEM_LEGACY_MULTI", f"{base.API_BASE}/items?ids={ITEM_ID}&attributes=id,title,status,permalink,price,original_price"),
        ("ITEM_PRICES", f"{base.API_BASE}/items/{ITEM_ID}/prices"),
    ]

    for label, url in calls:
        call(label, url, token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
