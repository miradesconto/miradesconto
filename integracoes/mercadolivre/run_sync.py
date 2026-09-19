#!/usr/bin/env python3
"""Entry-point da sincronização Mercado Livre.

Aceita pequenas variações do envelope retornado pelo endpoint /items/bulk e
registra diagnóstico curto sem expor credenciais.
"""
from __future__ import annotations

import json
import time
from urllib.parse import quote

import sync_catalog as base


def parse_row(row: dict):
    response = row.get("response") if isinstance(row.get("response"), dict) else {}
    body = row.get("body") if isinstance(row.get("body"), dict) else {}
    if not body and isinstance(response.get("body"), dict):
        body = response["body"]
    if not body and response and any(k in response for k in ("id", "title", "price", "status")):
        body = response

    item_id = str(
        row.get("id")
        or response.get("id")
        or body.get("id")
        or ""
    ).strip()

    raw_status = (
        row.get("status_code")
        or row.get("code")
        or row.get("status")
        or response.get("status_code")
        or response.get("code")
        or response.get("status")
        or 0
    )
    try:
        status_code = int(raw_status)
    except (TypeError, ValueError):
        status_code = 0

    message = (
        row.get("message")
        or response.get("message")
        or body.get("message")
        or "consulta não concluída"
    )
    return item_id, status_code, body, message


def fetch_items(ids: list[str], access_token: str):
    results: dict[str, dict] = {}
    errors: list[dict] = []
    attributes = ",".join([
        "body.id", "body.title", "body.price", "body.original_price",
        "body.permalink", "body.status",
    ])
    headers = {"Authorization": f"Bearer {access_token}"}
    total_batches = (len(ids) + base.BATCH_SIZE - 1) // base.BATCH_SIZE

    for number, batch in enumerate(base.chunks(ids, base.BATCH_SIZE), start=1):
        id_param = quote(",".join(batch), safe=",")
        attr_param = quote(attributes, safe=",")
        url = f"{base.API_BASE}/items/bulk?ids={id_param}&attributes={attr_param}"
        payload = base.http_json(url, headers=headers)
        if not isinstance(payload, list):
            raise RuntimeError(f"Resposta inesperada de /items/bulk no lote {number}.")

        diagnostics = []
        for row in payload:
            if not isinstance(row, dict):
                continue
            item_id, status_code, body, message = parse_row(row)

            if item_id and status_code in {200, 206}:
                results[item_id] = body
            else:
                errors.append({
                    "id": item_id or None,
                    "status_code": status_code or None,
                    "message": message,
                })
                if len(diagnostics) < 3:
                    diagnostics.append({
                        "row_keys": sorted(row.keys()),
                        "id": item_id or None,
                        "status_code": status_code or None,
                        "message": message,
                        "body_keys": sorted(body.keys())[:12],
                        "raw": row,
                    })

        if number == 1 and diagnostics:
            print("DIAGNOSTICO_PRIMEIRO_LOTE=" + json.dumps(diagnostics, ensure_ascii=False)[:6000])
        print(f"Lote {number}/{total_batches}: {len(batch)} itens consultados")
        time.sleep(0.08)

    return results, errors


base.fetch_items = fetch_items

if __name__ == "__main__":
    try:
        raise SystemExit(base.main())
    except Exception as exc:
        print(f"ERRO: {exc}", file=base.sys.stderr)
        raise SystemExit(1)
