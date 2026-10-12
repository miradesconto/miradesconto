"""Importa CSV de links Shopee para o schema 2, sem inventar preço ou estoque."""
from __future__ import annotations

import argparse
import csv
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlsplit

from schema import CatalogError, build_catalog, secure_url, write_preview, AFFILIATE_HOSTS


def parse_brl(value):
    raw = str(value or "").strip().replace("R$", "").replace(" ", "")
    if not re.fullmatch(r"\d+(?:\.\d{3})*(?:,\d{1,2})?|\d+(?:,\d{1,2})?", raw):
        raise CatalogError("Preço BRL inválido: " + raw)
    try:
        value = float(Decimal(raw.replace(".", "").replace(",", ".")))
    except InvalidOperation as exc:
        raise CatalogError("Preço BRL inválido") from exc
    if value <= 0:
        raise CatalogError("Preço precisa ser positivo")
    return value


def field(row, *keys):
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def read_shopee_csv(path, only_ids=None, mapping=None):
    only_ids = set(only_ids) if only_ids is not None else None
    mapping = mapping or {}
    products = []
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise CatalogError("CSV Shopee sem cabeçalho")
        for number, row in enumerate(reader, 2):
            if not any(row.values()):
                continue
            item_id = field(row, "Item Id", "item_id")
            if only_ids is not None and item_id not in only_ids:
                continue
            if not item_id.isdigit():
                raise CatalogError(f"Linha {number}: ID inválido")
            original = field(row, "Product Link", "product_url")
            link = field(row, "Offer Link", "affiliate_url")
            secure_url(original, {"shopee.com.br", "www.shopee.com.br"})
            match = re.fullmatch(r"/product/\d+/(\d+)", urlsplit(original).path)
            if not match or match.group(1) != item_id:
                raise CatalogError(f"Linha {number}: anúncio não corresponde ao item")
            secure_url(link, AFFILIATE_HOSTS["shopee"])
            # O link afiliado deve ser o curto exportado, nunca apenas o link do anúncio.
            if urlsplit(link).hostname not in {"s.shopee.com.br", "shope.ee"}:
                raise CatalogError(f"Linha {number}: falta link curto afiliado")
            title = field(row, "Item Name", "title")
            if not title:
                raise CatalogError(f"Linha {number}: sem título")
            image = field(row, "image_url", "Image URL") or None
            if image:
                secure_url(image)
            universal_id = mapping.get(item_id, "prod_sp_" + item_id)
            price_text = field(row, "Price", "price_brl")
            # Valores abreviados como '1,5mil' não são preços exatos.
            if re.fullmatch(r"\d+(?:,\d+)?mil", price_text, flags=re.IGNORECASE):
                parsed_price = None
            else:
                parsed_price = parse_brl(price_text)
            product = {
                "id": universal_id, "title": title,
                "description": "", "category": field(row, "category") or "Tecnologia",
                "image_url": image, "featured": False,
                "offers": [{
                    "platform": "shopee", "platform_id": item_id,
                    "affiliate_url": link, "product_url": original,
                    "price": parsed_price,
                    "currency": "BRL", "in_stock": None,
                    "price_status": "missing" if parsed_price is None else "unverified", "price_verified_at": None,
                    "price_observed_on": field(row, "source_date") or None,
                    "seller": field(row, "Nome da loja", "merchant"),
                    "source": "shopee_csv",
                }]
            }
            products.append(product)
    if only_ids is not None and {x["offers"][0]["platform_id"] for x in products} != only_ids:
        raise CatalogError("IDs solicitados não estão todos presentes no CSV")
    return build_catalog(products)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--output", type=Path, required=True, help="Nova prévia JSON, sem sobrescrever")
    parser.add_argument("--only", help="IDs Shopee separados por vírgula")
    parser.add_argument("--map", type=Path, help="JSON: ID Shopee → ID interno aprovado")
    args = parser.parse_args()
    mapping = json.loads(args.map.read_text(encoding="utf-8")) if args.map else {}
    ids = [v.strip() for v in args.only.split(",") if v.strip()] if args.only else None
    catalog = read_shopee_csv(args.csv, ids, mapping)
    write_preview(catalog["products"], args.output)
    print(f"Prévia Shopee: {len(catalog['products'])} produtos; nenhum arquivo de produção alterado.")


if __name__ == "__main__":
    main()
