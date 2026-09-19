#!/usr/bin/env python3
"""Entry-point da sincronização atual do catálogo MiraDesconto.

Mantém uma base-reserva de 675 produtos oficiais para que falhas transitórias em
alguns links não façam o catálogo encolher a cada execução.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import rebuild_catalog

SEED_PATH = Path(__file__).with_name("catalogo-semente.json")
SEED_SOURCE_REF = "7878aafe602c3b0bb3df064746e5282f9c54b61f"
SEED_LIMIT = 675


def parse_produtos_js(text: str) -> dict:
    match = re.search(r"window\.MIRA_DATA\s*=\s*(\{.*\})\s*;?\s*$", text, flags=re.S)
    if not match:
        raise RuntimeError("Não foi possível ler o catálogo histórico para criar a reserva.")
    data = json.loads(match.group(1))
    products = data.get("products")
    if not isinstance(products, list) or len(products) < SEED_LIMIT:
        raise RuntimeError("O catálogo histórico não contém produtos suficientes para a reserva.")
    return {
        "createdFrom": SEED_SOURCE_REF,
        "purpose": "reserva de links oficiais para reposição durante sincronizações",
        "products": products[:SEED_LIMIT],
    }


def ensure_seed() -> dict:
    if SEED_PATH.exists():
        data = json.loads(SEED_PATH.read_text(encoding="utf-8"))
        products = data.get("products") if isinstance(data, dict) else None
        if isinstance(products, list) and len(products) >= 500:
            return data
        raise RuntimeError("catalogo-semente.json existe, mas está incompleto.")

    try:
        text = subprocess.check_output(
            ["git", "show", f"{SEED_SOURCE_REF}:produtos.js"],
            text=True,
            encoding="utf-8",
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("Não foi possível recuperar o catálogo histórico para criar a reserva.") from exc

    data = parse_produtos_js(text)
    SEED_PATH.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Catálogo semente criado com {len(data['products'])} produtos.")
    return data


def load_seed_data() -> dict:
    seed = ensure_seed()
    return {"products": seed["products"]}


if __name__ == "__main__":
    try:
        # O rebuild usa a reserva fixa, não apenas os produtos publicados na
        # execução anterior. Assim consegue substituir links que falharam.
        rebuild_catalog.base.load_mira_data = load_seed_data
        # Se a atualização não conseguir manter pelo menos 450 ofertas válidas,
        # preservamos o catálogo anterior em vez de publicar uma vitrine degradada.
        sys.argv = [sys.argv[0], "--max-products", "500", "--min-products", "450"]
        raise SystemExit(rebuild_catalog.main())
    except Exception as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        raise SystemExit(1)
