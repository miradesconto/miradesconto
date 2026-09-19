#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRODUTOS_JS = ROOT / "produtos.js"
DATA_PRODUTOS = ROOT / "_data" / "produtos.json"
MIN_PRODUCTS = 450
MAX_FEATURED = 12


def load_catalog() -> dict:
    text = PRODUTOS_JS.read_text(encoding="utf-8")
    match = re.search(r"window\.MIRA_DATA\s*=\s*(\{.*\})\s*;?\s*$", text, flags=re.S)
    if not match:
        raise RuntimeError("produtos.js não contém window.MIRA_DATA válido")
    data = json.loads(match.group(1))
    if not isinstance(data.get("products"), list):
        raise RuntimeError("catálogo sem lista products")
    return data


def valid_http(value: object) -> bool:
    return isinstance(value, str) and value.startswith(("https://", "http://"))


def main() -> int:
    data = load_catalog()
    products = data["products"]
    errors: list[str] = []
    warnings: list[str] = []

    if len(products) < MIN_PRODUCTS:
        errors.append(f"catálogo caiu para {len(products)} produtos; mínimo seguro: {MIN_PRODUCTS}")

    ids: list[str] = []
    featured = 0
    for index, product in enumerate(products, start=1):
        if not isinstance(product, dict):
            errors.append(f"produto #{index} não é objeto")
            continue

        item_id = str(product.get("id") or "")
        ids.append(item_id)
        if not re.fullmatch(r"MLB\d{7,}", item_id):
            errors.append(f"ID inválido na posição {index}: {item_id!r}")
        if not str(product.get("name") or "").strip():
            errors.append(f"{item_id or index}: nome vazio")
        try:
            price = float(product.get("price"))
        except (TypeError, ValueError):
            price = 0
        if price <= 0:
            errors.append(f"{item_id or index}: preço inválido")
        affiliate = str(product.get("affiliateUrl") or "")
        if not affiliate.startswith("https://meli.la/"):
            errors.append(f"{item_id or index}: link de afiliado não é meli.la oficial")
        if not valid_http(product.get("imageUrl")):
            warnings.append(f"{item_id or index}: imagem ausente/inválida")
        if product.get("available") is False:
            warnings.append(f"{item_id or index}: marcado como indisponível")
        if product.get("featured") is True:
            featured += 1

    clean_ids = [item for item in ids if item]
    duplicate_count = len(clean_ids) - len(set(clean_ids))
    if duplicate_count:
        errors.append(f"{duplicate_count} IDs duplicados no catálogo")
    if featured > MAX_FEATURED:
        errors.append(f"{featured} produtos em destaque; máximo esperado: {MAX_FEATURED}")

    if not DATA_PRODUTOS.exists():
        errors.append("_data/produtos.json ausente")
    else:
        public_data = json.loads(DATA_PRODUTOS.read_text(encoding="utf-8"))
        if not isinstance(public_data, dict):
            errors.append("_data/produtos.json inválido")
        else:
            missing = [item for item in clean_ids if item not in public_data]
            if missing:
                errors.append(f"{len(missing)} produtos não aparecem em _data/produtos.json")

    published_articles = 0
    stale_article_products = 0
    for article in (ROOT / "_artigos").glob("*.md"):
        text = article.read_text(encoding="utf-8")
        if re.search(r'^status:\s*["\']?publicado["\']?\s*$', text, flags=re.M):
            published_articles += 1
            for item_id in re.findall(r"MLB\d{7,}", text):
                if item_id not in set(clean_ids):
                    stale_article_products += 1

    summary = {
        "ok": not errors,
        "products": len(products),
        "featured": featured,
        "published_articles": published_articles,
        "article_product_refs_outside_current_catalog": stale_article_products,
        "warnings": len(warnings),
        "errors": errors,
        "collectedAt": data.get("collectedAt"),
    }
    print(json.dumps(summary, ensure_ascii=False))
    if warnings:
        print("Avisos:")
        for warning in warnings[:20]:
            print(f"- {warning}")
    if errors:
        print("Erros:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
