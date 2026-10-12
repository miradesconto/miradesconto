"""Parser de CSV Amazon com links afiliados FORNECIDOS pelo titular; sem API ou geração de tags."""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from schema import CatalogError, build_catalog, secure_url, write_preview, AFFILIATE_HOSTS
from import_shopee import parse_brl


def read_amazon_csv(path, mapping=None):
    mapping = mapping or {}
    products = []
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"asin", "title", "affiliate_url"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise CatalogError("CSV Amazon precisa de asin,title,affiliate_url")
        for number, row in enumerate(reader, 2):
            asin = str(row.get("asin") or "").strip().upper()
            if not re.fullmatch(r"[A-Z0-9]{10}", asin):
                raise CatalogError(f"Linha {number}: ASIN inválido")
            link = str(row.get("affiliate_url") or "").strip()
            secure_url(link, AFFILIATE_HOSTS["amazon"])
            url = urlsplit(link)
            # Link direto sem tag de associado não é tratado como link de afiliado.
            if url.hostname != "amzn.to" and not parse_qs(url.query).get("tag"):
                raise CatalogError(f"Linha {number}: link direto Amazon sem tag= explícita")
            original = str(row.get("product_url") or "").strip() or None
            if original:
                secure_url(original, AFFILIATE_HOSTS["amazon"])
            img = str(row.get("image_url") or "").strip() or None
            if img:
                secure_url(img)
            title = str(row.get("title") or "").strip()
            if not title:
                raise CatalogError(f"Linha {number}: sem título")
            price_txt = str(row.get("price") or "").strip()
            products.append({
                "id": mapping.get(asin, "prod_amazon_" + asin.lower()),
                "title": title, "description": str(row.get("description") or ""),
                "category": str(row.get("category") or "Tecnologia"),
                "image_url": img, "featured": False,
                "offers": [{
                    "platform": "amazon", "platform_id": asin,
                    "affiliate_url": link, "product_url": original,
                    "price": parse_brl(price_txt) if price_txt else None,
                    "currency": "BRL", "in_stock": None,
                    "price_status": "unverified", "price_verified_at": None,
                    "source": "amazon_csv",
                }],
            })
    return build_catalog(products)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--map", type=Path)
    args = ap.parse_args()
    mapping = json.loads(args.map.read_text(encoding="utf-8")) if args.map else {}
    catalog = read_amazon_csv(args.csv, mapping)
    write_preview(catalog["products"], args.output)
    print(f"Prévia Amazon: {len(catalog['products'])} produtos. Os links não foram verificados por compra.")


if __name__ == "__main__":
    main()
