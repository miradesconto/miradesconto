#!/usr/bin/env python3
"""Entry-point da sincronização atual do catálogo MiraDesconto."""
from __future__ import annotations

import sys

import rebuild_catalog


if __name__ == "__main__":
    try:
        # Limite conservador para manter o site leve e trava de segurança para
        # nunca substituir o catálogo por um resultado anormalmente pequeno.
        sys.argv = [sys.argv[0], "--max-products", "500", "--min-products", "40"]
        raise SystemExit(rebuild_catalog.main())
    except Exception as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        raise SystemExit(1)
