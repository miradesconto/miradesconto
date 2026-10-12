"""Adaptador read-only para JSON do Mercado Livre legado; não altera sincronizações."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from schema import build_catalog, from_legacy_ml, write_preview, CatalogError


def read_mercadolivre_json(path, mapping=None):
    mapping = mapping or {}
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    products = payload.get("products") if isinstance(payload, dict) else payload
    if not isinstance(products, list):
        raise CatalogError("JSON ML deve conter lista de produtos")
    out = []
    for p in products:
        if not isinstance(p, dict) or not p.get("affiliateUrl") and not p.get("affiliate_url"):
            continue
        out.append(from_legacy_ml(p, mapping.get(p["id"])))
    return build_catalog(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("json", type=Path, help="JSON existente de leitura, ex.: dados/catalogo.json")
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--map", type=Path)
    args = ap.parse_args()
    mapping = json.loads(args.map.read_text(encoding="utf-8")) if args.map else {}
    catalog = read_mercadolivre_json(args.json, mapping)
    write_preview(catalog["products"], args.output)
    print(f"Prévia ML: {len(catalog['products'])} produtos; pipeline original intocado.")


if __name__ == "__main__":
    main()
