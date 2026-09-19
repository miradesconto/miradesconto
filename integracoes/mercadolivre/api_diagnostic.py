#!/usr/bin/env python3
"""Diagnóstico mínimo da API do Mercado Livre sem expor dados pessoais."""
from __future__ import annotations

import json
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

import sync_catalog as base

ITEM_ID = "MLB4592320910"
APP_ID = "5739104192519635"
USER_ID = "3690746229"
HIGHLIGHT_CATEGORY = "MLB432825"
AFFILIATE_BASE = "https://www.mercadolivre.com.br"
KNOWN_AFFILIATE_URL = "https://meli.la/1TJh5DW"


def _decode(response):
    raw = response.read().decode("utf-8", errors="replace")
    try:
        return json.loads(raw)
    except Exception:
        return {"raw": raw[:300]}


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
            return response.status, _decode(response)
    except HTTPError as exc:
        return exc.code, _decode(exc)


def post_json(url: str, token: str, body: dict):
    raw_body = json.dumps(body).encode("utf-8")
    req = Request(
        url,
        data=raw_body,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "MiraDesconto/1.0 (+https://miradesconto.github.io/miradesconto/)",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=45) as response:
            return response.status, _decode(response)
    except HTTPError as exc:
        return exc.code, _decode(exc)


def resolve_affiliate_url(url: str) -> tuple[str, dict[str, list[str]]]:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"}, method="GET")
    with urlopen(req, timeout=45) as response:
        final_url = response.geturl()
    return final_url, parse_qs(urlparse(final_url).query)


def print_status(label: str, status: int, payload) -> None:
    out = {"http": status}
    if isinstance(payload, dict):
        if payload.get("error"):
            out["error"] = payload.get("error")
        if payload.get("message"):
            out["message"] = payload.get("message")
        paging = payload.get("paging")
        if isinstance(paging, dict) and "total" in paging:
            out["total"] = paging.get("total")
        content = payload.get("content")
        if isinstance(content, list):
            out["count"] = len(content)
        results = payload.get("results")
        if isinstance(results, list):
            out["count"] = len(results)
        tags = payload.get("tags")
        if isinstance(tags, list):
            out["count"] = len(tags)
            out["has_active_tag"] = any(isinstance(t, dict) and t.get("in_use") for t in tags)
        if "raw" in payload:
            raw = str(payload.get("raw") or "").lower()
            out["html_like"] = "<html" in raw or "<!doctype" in raw
    elif isinstance(payload, list) and payload:
        row = payload[0] if isinstance(payload[0], dict) else {}
        if row:
            out["item_status"] = row.get("status_code") or row.get("code")
            err = row.get("error") if isinstance(row.get("error"), dict) else {}
            if err.get("message"):
                out["message"] = err.get("message")
    print(f"{label}=" + json.dumps(out, ensure_ascii=False))


def product_summary(product_id: str, token: str) -> dict:
    status, product = request_json(f"{base.API_BASE}/products/{product_id}", token)
    summary = {"http": status, "product_id": product_id}
    if status == 200 and isinstance(product, dict):
        summary.update({
            "status": product.get("status"),
            "name": product.get("name"),
            "permalink": product.get("permalink"),
        })
        winner = product.get("buy_box_winner")
        if isinstance(winner, dict):
            summary["buy_box_winner"] = {
                "item_id": winner.get("item_id"),
                "price": winner.get("price"),
                "currency_id": winner.get("currency_id"),
                "available_quantity": winner.get("available_quantity"),
            }
    elif isinstance(product, dict):
        summary["error"] = product.get("error")
        summary["message"] = product.get("message")
    return summary


def main() -> int:
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
    print("GRANT=" + json.dumps({"http": status, "scopes": grant_scopes}, ensure_ascii=False))

    status, payload = request_json(f"{base.API_BASE}/users/{USER_ID}/items/search?limit=1", token)
    total = None
    if isinstance(payload, dict) and isinstance(payload.get("paging"), dict):
        total = payload["paging"].get("total")
    print("OWN_ITEMS_SEARCH=" + json.dumps({"http": status, "total": total}))

    status, catalog = request_json(
        f"{base.API_BASE}/products/search?status=active&site_id=MLB&q=Samsung",
        token,
    )
    print_status("CATALOG_PRODUCTS_SEARCH", status, catalog)

    sample_product_url = None
    if status == 200 and isinstance(catalog, dict):
        results = catalog.get("results")
        if isinstance(results, list) and results and isinstance(results[0], dict):
            product_id = results[0].get("id")
            if product_id:
                print("CATALOG_PRODUCT_DETAIL=" + json.dumps(product_summary(product_id, token), ensure_ascii=False))
                sample_product_url = f"https://www.mercadolivre.com.br/p/{product_id}"

    status, highlights = request_json(
        f"{base.API_BASE}/highlights/MLB/category/{HIGHLIGHT_CATEGORY}",
        token,
    )
    print_status("HIGHLIGHTS_CATEGORY", status, highlights)

    if status == 200 and isinstance(highlights, dict):
        content = highlights.get("content")
        if isinstance(content, list):
            highlighted_product_id = None
            for row in content:
                if isinstance(row, dict) and row.get("type") == "PRODUCT" and row.get("id"):
                    highlighted_product_id = row.get("id")
                    break
            if highlighted_product_id:
                print("HIGHLIGHT_PRODUCT_DETAIL=" + json.dumps(product_summary(highlighted_product_id, token), ensure_ascii=False))

    # Testa se o OAuth do DevCenter também autentica a Central de Afiliados.
    status, affiliate_tags = request_json(
        f"{AFFILIATE_BASE}/affiliate-program/api/v2/stripe/user/tags",
        token,
    )
    print_status("AFFILIATE_TAGS_WITH_OAUTH", status, affiliate_tags)

    # Extrai somente a presença dos identificadores de um link de afiliado já existente.
    derived_tag = None
    try:
        _, params = resolve_affiliate_url(KNOWN_AFFILIATE_URL)
        has_word = bool(params.get("matt_word"))
        has_tool = bool(params.get("matt_tool") or params.get("matt_tool_id"))
        derived_tag = (params.get("matt_word") or [None])[0]
        print("KNOWN_AFFILIATE_REDIRECT=" + json.dumps({
            "resolved": True,
            "has_matt_word": has_word,
            "has_matt_tool": has_tool,
        }))
    except Exception as exc:
        print("KNOWN_AFFILIATE_REDIRECT=" + json.dumps({"resolved": False, "error_type": type(exc).__name__}))

    # Sem expor a tag, tenta usar OAuth diretamente no endpoint interno de criação de links.
    if derived_tag and sample_product_url:
        status, generated = post_json(
            f"{AFFILIATE_BASE}/affiliate-program/api/v2/stripe/user/links",
            token,
            {"url": sample_product_url, "tag": derived_tag},
        )
        print("AFFILIATE_LINK_WITH_OAUTH=" + json.dumps({
            "http": status,
            "json": isinstance(generated, dict) and "raw" not in generated,
            "has_short_url": isinstance(generated, dict) and bool(generated.get("short_url")),
            "html_like": isinstance(generated, dict) and "raw" in generated and (
                "<html" in str(generated.get("raw") or "").lower()
                or "<!doctype" in str(generated.get("raw") or "").lower()
            ),
        }))

    status, affiliate_hub = post_json(
        f"{AFFILIATE_BASE}/affiliate-program/api/hub/search?is_affiliate=true&device=desktop",
        token,
        {"search": "", "sort": "relevance", "filters": [{"id": "best_seller", "value": True}], "offset": 0},
    )
    polycards = None
    if isinstance(affiliate_hub, dict):
        model = affiliate_hub.get("polycard_client_model")
        if isinstance(model, dict) and isinstance(model.get("polycards"), list):
            polycards = len(model["polycards"])
    print("AFFILIATE_HUB_WITH_OAUTH=" + json.dumps({
        "http": status,
        "json": isinstance(affiliate_hub, dict) and "raw" not in affiliate_hub,
        "polycards": polycards,
        "html_like": isinstance(affiliate_hub, dict) and "raw" in affiliate_hub and (
            "<html" in str(affiliate_hub.get("raw") or "").lower()
            or "<!doctype" in str(affiliate_hub.get("raw") or "").lower()
        ),
    }))

    checks = [
        ("PUBLIC_SEARCH_LEGACY", f"{base.API_BASE}/sites/MLB/search?q=camiseta&limit=1"),
        ("ITEM_SINGLE", f"{base.API_BASE}/items/{ITEM_ID}"),
        ("ITEM_BULK", f"{base.API_BASE}/items/bulk?ids={ITEM_ID}"),
        ("ITEM_SALE_PRICE", f"{base.API_BASE}/items/{ITEM_ID}/sale_price"),
        ("ITEM_PRICES", f"{base.API_BASE}/items/{ITEM_ID}/prices"),
    ]
    for label, url in checks:
        status, payload = request_json(url, token)
        print_status(label, status, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
