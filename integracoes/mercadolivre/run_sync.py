#!/usr/bin/env python3
"""Atualiza preços a partir do cadastro principal, preservando registros fora da vitrine."""
import sys
from pathlib import Path
import rebuild_catalog

ROOT = Path(__file__).resolve().parents[2]


def load_registered_data():
    catalog = rebuild_catalog.base.catalogo.load(ROOT)
    return {"products": catalog["products"]}


if __name__ == "__main__":
    try:
        rebuild_catalog.main(
            argv=["--max-products", "500", "--min-products", "450", *sys.argv[1:]],
            source=load_registered_data(),
        )
    except Exception as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        raise SystemExit(1)
