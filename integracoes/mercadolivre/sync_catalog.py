#!/usr/bin/env python3
"""Atualiza o catálogo público do MiraDesconto usando a API oficial do Mercado Livre.

Segurança:
- Nunca grava Client Secret, access token ou refresh token no repositório.
- Prefere OAuth client_credentials para automação server-to-server.
- Pode usar ML_ACCESS_TOKEN diretamente para testes locais.
- Pode usar ML_REFRESH_TOKEN como fallback quando disponível.

Arquivos atualizados em uma execução completa:
- produtos.js
- catalogo/produtos-*.json
- _data/produtos.json
- integracoes/mercadolivre/ultimo-sync.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

API_BASE = "https://api.mercadolibre.com"
TOKEN_URL = f"{API_BASE}/oauth/token"
BATCH_SIZE = 20
ROOT = Path(__file__).resolve().parents[2]
PRODUTOS_JS = ROOT / "produtos.js"
CATALOGO_DIR = ROOT / "catalogo"
DATA_PRODUTOS = ROOT / "_data" / "produtos.json"
REPORT_PATH = ROOT / "integracoes" / "mercadolivre" / "ultimo-sync.json"


def now_sp() -> datetime:
    return datetime.now(ZoneInfo("America/Sao_Paulo"))


def mask_in_actions(value: str | None) -> None:
    if value and os.getenv("GITHUB_ACTIONS") == "true":
        print(f"::add-mask::{value}")


def http_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    form: dict[str, str] | None = None,
    attempts: int = 4,
) -> Any:
    body = None
    req_headers = {
        "Accept": "application/json",
        "User-Agent": "MiraDesconto/1.0 (+https://miradesconto.github.io/miradesconto/)",
    }
    if headers:
        req_headers.update(headers)
    if form is not None:
        body = urlencode(form).encode("utf-8")
        req_headers["Content-Type"] = "application/x-www-form-urlencoded"

    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        req = Request(url, data=body, headers=req_headers, method=method)
        try:
            with urlopen(req, timeout=45) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw)
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            last_error = RuntimeError(f"HTTP {exc.code} em {url}: {detail[:500]}")
            if exc.code not in {429, 500, 502, 503, 504} or attempt == attempts:
                raise last_error
            time.sleep(min(2 ** attempt, 12))
        except (URLError, TimeoutError) as exc:
            last_error = exc
            if attempt == attempts:
                raise RuntimeError(f"Falha de rede em {url}: {exc}") from exc
            time.sleep(min(2 ** attempt, 12))
    raise RuntimeError(str(last_error))


def get_access_token() -> tuple[str, str]:
    direct = os.getenv("ML_ACCESS_TOKEN", "").strip()
    if direct:
        mask_in_actions(direct)
        return direct, "access_token"

    client_id = os.getenv("ML_CLIENT_ID", "").strip()
    client_secret = os.getenv("ML_CLIENT_SECRET", "").strip()
    refresh_token = os.getenv("ML_REFRESH_TOKEN", "").strip()

    if not client_id or not client_secret:
        raise RuntimeError(
            "Defina ML_CLIENT_ID e ML_CLIENT_SECRET. "
            "O Client Secret deve existir apenas em GitHub Actions Secrets/variável local."
        )

    # Fluxo preferido para rotina automática: não exige persistir refresh token rotativo.
    try:
        response = http_json(
            TOKEN_URL,
            method="POST",
            form={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
        )
        token = str(response.get("access_token") or "").strip()
        if token:
            mask_in_actions(token)
            return token, "client_credentials"
    except Exception as client_exc:
        if not refresh_token:
            raise RuntimeError(
                "Não foi possível obter token por client_credentials. "
                "Verifique se esse fluxo está habilitado na aplicação do Mercado Livre. "
                f"Detalhe: {client_exc}"
            ) from client_exc

    # Fallback: útil para teste/recuperação. O Mercado Livre pode rotacionar o refresh token.
    response = http_json(
        TOKEN_URL,
        method="POST",
        form={
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
        },
    )
    token = str(response.get("access_token") or "").strip()
    new_refresh = str(response.get("refresh_token") or "").strip()
    if not token:
        raise RuntimeError("Resposta OAuth sem access_token.")
    mask_in_actions(token)
    mask_in_actions(new_refresh)
    if new_refresh and new_refresh != refresh_token:
        print(
            "AVISO: o refresh token foi rotacionado. Prefira habilitar client_credentials "
            "para a automação do MiraDesconto."
        )
    return token, "refresh_token"


def load_mira_data() -> dict[str, Any]:
    text = PRODUTOS_JS.read_text(encoding="utf-8")
    match = re.search(r"window\.MIRA_DATA\s*=\s*(\{.*\})\s*;?\s*$", text, flags=re.S)
    if not match:
        raise RuntimeError("Não encontrei window.MIRA_DATA em produtos.js.")
    data = json.loads(match.group(1))
    if not isinstance(data.get("products"), list):
        raise RuntimeError("produtos.js não contém products como lista.")
    return data


def chunks(values: list[str], size: int):
    for index in range(0, len(values), size):
        yield values[index : index + size]


def fetch_items(ids: list[str], access_token: str) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    results: dict[str, dict[str, Any]] = {}
    errors: list[dict[str, Any]] = []
    attributes = ",".join(
        [
            "body.id",
            "body.title",
            "body.price",
            "body.original_price",
            "body.permalink",
            "body.status",
        ]
    )
    headers = {"Authorization": f"Bearer {access_token}"}

    total_batches = (len(ids) + BATCH_SIZE - 1) // BATCH_SIZE
    for number, batch in enumerate(chunks(ids, BATCH_SIZE), start=1):
        id_param = quote(",".join(batch), safe=",")
        attr_param = quote(attributes, safe=",")
        url = f"{API_BASE}/items/bulk?ids={id_param}&attributes={attr_param}"
        payload = http_json(url, headers=headers)
        if not isinstance(payload, list):
            raise RuntimeError(f"Resposta inesperada do endpoint bulk no lote {number}.")

        for row in payload:
            if not isinstance(row, dict):
                continue
            item_id = str(row.get("id") or row.get("body", {}).get("id") or "").strip()
            status_code = int(row.get("status_code") or row.get("code") or 0)
            body = row.get("body") if isinstance(row.get("body"), dict) else {}
            if item_id and status_code == 200:
                results[item_id] = body
            else:
                errors.append(
                    {
                        "id": item_id or None,
                        "status_code": status_code or None,
                        "message": row.get("message") or body.get("message") or "consulta não concluída",
                    }
                )
        print(f"Lote {number}/{total_batches}: {len(batch)} itens consultados")
        time.sleep(0.08)

    return results, errors


def valid_number(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        number = float(value)
        if number > 0:
            return round(number, 2)
    return None


def update_product(product: dict[str, Any], api_item: dict[str, Any], date_text: str) -> bool:
    before = json.dumps(product, ensure_ascii=False, sort_keys=True)

    title = api_item.get("title")
    if isinstance(title, str) and title.strip():
        product["name"] = title.strip()

    current_price = valid_number(api_item.get("price"))
    if current_price is not None:
        product["price"] = current_price

        original_price = valid_number(api_item.get("original_price"))
        if original_price is not None and original_price > current_price:
            product["oldPrice"] = original_price
            discount = round((1 - current_price / original_price) * 100, 4)
            product["discount"] = discount
            product["displayedDiscount"] = f"{round(discount)}% OFF"
        else:
            product["oldPrice"] = None
            product["discount"] = None
            product["displayedDiscount"] = None

    permalink = api_item.get("permalink")
    if isinstance(permalink, str) and permalink.startswith("http"):
        product["productUrl"] = permalink

    status = str(api_item.get("status") or "").lower()
    if status:
        product["available"] = status == "active"

    product["collectedAt"] = date_text

    after = json.dumps(product, ensure_ascii=False, sort_keys=True)
    return before != after


def write_produtos_js(data: dict[str, Any]) -> None:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    PRODUTOS_JS.write_text(
        "// Dados do catálogo; preços e status podem ser atualizados pela API oficial do Mercado Livre.\n"
        f"window.MIRA_DATA = {payload};\n",
        encoding="utf-8",
    )


def write_catalog_chunks(products: list[dict[str, Any]]) -> int:
    CATALOGO_DIR.mkdir(parents=True, exist_ok=True)
    compact_keys = [
        "id",
        "name",
        "category",
        "price",
        "oldPrice",
        "discount",
        "affiliateUrl",
        "imageUrl",
        "rank",
        "featured",
        "available",
    ]
    chunks_written = 0
    expected: set[Path] = set()

    for index in range(0, len(products), 100):
        number = index // 100 + 1
        path = CATALOGO_DIR / f"produtos-{number:03d}.json"
        expected.add(path)
        batch = []
        for product in products[index : index + 100]:
            batch.append({key: product.get(key) for key in compact_keys if key in product})
        path.write_text(
            json.dumps(batch, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        chunks_written += 1

    for path in CATALOGO_DIR.glob("produtos-*.json"):
        if path not in expected:
            path.unlink()

    return chunks_written


def write_data_products(products: list[dict[str, Any]]) -> None:
    current: dict[str, Any] = {}
    if DATA_PRODUTOS.exists():
        try:
            loaded = json.loads(DATA_PRODUTOS.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                current = loaded
        except Exception:
            current = {}

    for product in products:
        item_id = str(product.get("id") or "").strip()
        if not item_id:
            continue
        entry = current.get(item_id) if isinstance(current.get(item_id), dict) else {}
        entry["name"] = product.get("name")
        entry["imageUrl"] = product.get("imageUrl")
        entry["available"] = product.get("available", True) is not False
        current[item_id] = entry

    DATA_PRODUTOS.parent.mkdir(parents=True, exist_ok=True)
    DATA_PRODUTOS.write_text(
        json.dumps(current, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_report(report: dict[str, Any]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="Consulta somente os primeiros N itens.")
    parser.add_argument("--dry-run", action="store_true", help="Consulta e valida, mas não grava arquivos.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data = load_mira_data()
    products: list[dict[str, Any]] = data["products"]
    candidates = [p for p in products if isinstance(p, dict) and str(p.get("id") or "").startswith("MLB")]
    if args.limit > 0:
        candidates = candidates[: args.limit]

    ids = [str(p["id"]) for p in candidates]
    if not ids:
        raise RuntimeError("Nenhum ID MLB encontrado no catálogo.")

    access_token, auth_mode = get_access_token()
    api_items, errors = fetch_items(ids, access_token)
    if not api_items:
        raise RuntimeError("A API não retornou nenhum item válido; nada foi alterado.")

    timestamp = now_sp()
    date_text = timestamp.strftime("%d/%m/%Y")
    changed = 0
    inactive = 0

    for product in candidates:
        item_id = str(product.get("id"))
        api_item = api_items.get(item_id)
        if not api_item:
            continue
        if str(api_item.get("status") or "").lower() != "active":
            inactive += 1
        if update_product(product, api_item, date_text):
            changed += 1

    report = {
        "updatedAt": timestamp.isoformat(timespec="seconds"),
        "source": "Mercado Livre API",
        "endpoint": "/items/bulk",
        "authentication": auth_mode,
        "requested": len(ids),
        "successful": len(api_items),
        "changed": changed,
        "inactive": inactive,
        "errors": errors[:100],
        "dryRun": bool(args.dry_run),
        "limit": args.limit or None,
    }

    print(json.dumps({key: report[key] for key in ["requested", "successful", "changed", "inactive", "dryRun"]}, ensure_ascii=False))

    if args.dry_run:
        return 0

    # Só marca a coleta global como atualizada quando a execução cobre o catálogo completo.
    if args.limit <= 0:
        data["collectedAt"] = date_text
        data["apiSync"] = {
            "source": "Mercado Livre API",
            "updatedAt": timestamp.isoformat(timespec="seconds"),
            "endpoint": "/items/bulk",
        }

    write_produtos_js(data)
    chunks_written = write_catalog_chunks(products)
    write_data_products(products)
    report["catalogFiles"] = chunks_written
    write_report(report)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        raise SystemExit(1)
