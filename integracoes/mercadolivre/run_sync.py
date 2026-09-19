#!/usr/bin/env python3
"""Entry-point da sincronização Mercado Livre.

Mantém compatibilidade com respostas HTTP 206 do recurso de itens e registra
um diagnóstico curto quando um lote não retorna itens utilizáveis.
"""
from __future__ import annotations

import json
import time
from urllib.parse import quote

import sync_catalog as base


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
            body = row.get("body") if isinstance(row.get("body"), dict) else {}
            item_id = str(row.get("id") or body.get("id") or "").strip()
            status_code = int(row.get("status_code") or row.get("code") or 0)

            if item_id and status_code in {200, 206}:
                results[item_id] = body
            else:
                message = row.get("message") or body.get("message") or "consulta não concluída"
                errors.append({
                    "id": item_id or None,
                    "status_code": status_code or None,
                    "message": message,
                })
                if len(diagnostics) < 3:
                    diagnostics.append({
                        "id": item_id or None,
                        "status_code": status_code or None,
                        "message": message,
                        "body_keys": sorted(body.keys())[:12],
                    })

        if number == 1 and diagnostics:
            print("DIAGNOSTICO_PRIMEIRO_LOTE=" + json.dumps(diagnostics, ensure_ascii=False))
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
