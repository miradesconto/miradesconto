"""Mescla prévias do schema 2; igualdade entre lojas exige mapeamento manual de ID."""
from __future__ import annotations

import argparse
import copy
from pathlib import Path
from schema import build_catalog, read_catalog, write_preview


def merge_catalogs(catalogs):
    by_id = {}
    for catalog in catalogs:
        for p in catalog["products"]:
            existing = by_id.get(p["id"])
            if existing is None:
                by_id[p["id"]] = copy.deepcopy(p)
            else:
                # Só agrupa variantes quando o operador informou o MESMO ID interno no mapeamento.
                existing["offers"].extend(copy.deepcopy(p["offers"]))
                if not existing["image_url"] and p.get("image_url"):
                    existing["image_url"] = p["image_url"]
    return build_catalog(list(by_id.values()))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("catalogs", nargs="+", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    merged = merge_catalogs([read_catalog(path) for path in args.catalogs])
    write_preview(merged["products"], args.output)
    print(f"Prévia unificada: {len(merged['products'])} produtos; sem publicação.")


if __name__ == "__main__":
    main()
