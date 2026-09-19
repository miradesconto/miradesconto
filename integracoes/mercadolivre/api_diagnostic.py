#!/usr/bin/env python3
"""Diagnóstico mínimo da API do Mercado Livre sem expor dados pessoais."""
from __future__ import annotations

import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import sync_catalog as base

ITEM_ID = "MLB4592320910"
APP_ID = "5739104192519635"
USER_ID = "3690746229"


def request_json(url: str, token: str):
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
            try:
                return response.status, json.loads(raw)
            except Exception:
                return response.status, {"raw": raw[:300]}
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(raw)
        except Exception:
            return exc.code, {"raw": raw[:300]}


def print_status(label: str, status: int, payload) -> None:
    out = {"http": status}
    if isinstance(payload, dict):
        if payload.get("error"):
            out["error"] = payload.get("error")
        if payload.get("message"):
            out["message"] = payload.get("message")
    elif isinstance(payload, list) and payload:
        row = payload[0] if isinstance(payload[0], dict) else {}
        if row:
            out["item_status"] = row.get("status_code") or row.get("code")
            err = row.get("error") if isinstance(row.get("error"), dict) else {}
            if err.get("message"):
                out["message"] = err.get("message")
    print(f"{label}=" + json.dumps(out, ensure_ascii=False))


def main() -> int:
    # Reinicialização pontual solicitada para testar o GitHub Secret atualizado.
    base.TOKEN_STATE_PATH.unlink(missing_ok=True)
    token, auth_mode = base.get_access_token()
    print(f"AUTH_MODE={auth_mode}")

    status, payload = request_json(f"{base.API_BASE}/users/me", token)
    print("USERS_ME=" + json.dumps({"http": status, "authenticated": status == 200}))

    status, payload = request_json(f"{base.API_BASE}/applications/{APP_ID}", token)
    app = payload if isinstance(payload, dict) else {}
    print("APPLICATION=" + json.dumps({
        "http": status,
        "active": app.get("active"),
        "blocked": app.get("blocked"),
        "certification_status": app.get("certification_status"),
        "scopes": app.get("scopes", []),
    }, ensure_ascii=False))

    status, payload = request_json(f"{base.API_BASE}/applications/{APP_ID}/grants", token)
    grant_scopes = []
    if isinstance(payload, dict) and isinstance(payload.get("grants"), list) and payload["grants"]:
        first = payload["grants"][0]
        if isinstance(first, dict):
            grant_scopes = first.get("scopes", [])
    rows = payload if isinstance(payload, list) else payload.get("grants", []) if isinstance(payload, dict) else []
    grants = [{"scopes": row.get("scopes", [])} for row in rows if isinstance(row, dict)]
    print("APPLICATION_GRANTS=" + json.dumps({"http": status, "grants": grants}, ensure_ascii=False))

    status, payload = request_json(f"{base.API_BASE}/users/{USER_ID}/items/search?limit=1", token)
    total = None
    if isinstance(payload, dict) and isinstance(payload.get("paging"), dict):
        total = payload["paging"].get("total")
    print("OWN_ITEMS_SEARCH=" + json.dumps({"http": status, "total": total}))

    checks = [
        ("PUBLIC_SEARCH", f"{base.API_BASE}/sites/MLB/search?q=camiseta&limit=1"),
        ("ITEM_SINGLE_NO_ATTRIBUTES", f"{base.API_BASE}/items/{ITEM_ID}"),
        ("ITEM_BULK_NO_ATTRIBUTES", f"{base.API_BASE}/items/bulk?ids={ITEM_ID}"),
        ("ITEM_PRICES", f"{base.API_BASE}/items/{ITEM_ID}/prices"),
    ]
    for label, url in checks:
        status, payload = request_json(url, token)
        print_status(label, status, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
