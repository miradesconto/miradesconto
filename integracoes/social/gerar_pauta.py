#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "integracoes"))
from qualidade import usable_price
PRODUTOS_JS = ROOT / "produtos.js"
OUT_JSON = Path(__file__).with_name("pauta-do-dia.json")
OUT_MD = Path(__file__).with_name("pauta-do-dia.md")
MAX_POSTS = 12
MAX_PER_CATEGORY = 2


def load_catalog() -> dict:
    text = PRODUTOS_JS.read_text(encoding="utf-8")
    match = re.search(r"window\.MIRA_DATA\s*=\s*(\{.*\})\s*;?\s*$", text, flags=re.S)
    if not match:
        raise RuntimeError("Não foi possível ler produtos.js")
    return json.loads(match.group(1))


def money(value: object) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    text = f"{number:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {text}"


def discount_value(product: dict) -> float:
    try:
        old = float(product.get("oldPrice") or 0)
        price = float(product.get("price") or 0)
    except (TypeError, ValueError):
        return 0
    return ((old - price) / old * 100) if old > price > 0 else 0


def eligible(product: dict) -> bool:
    try:
        price = float(product.get("price") or 0)
    except (TypeError, ValueError):
        price = 0
    return (
        bool(product.get("name"))
        and price > 0
        and str(product.get("affiliateUrl") or "").startswith("https://meli.la/")
        and str(product.get("imageUrl") or "").startswith("http")
        and product.get("available") is True
        and product.get("availabilityStatus") == "available"
        and usable_price(product)
    )


def choose(products: list[dict]) -> list[dict]:
    ranked = sorted(
        [p for p in products if eligible(p)],
        key=lambda p: (-discount_value(p), int(p.get("rank") or 999999)),
    )
    selected: list[dict] = []
    per_category: Counter[str] = Counter()
    selected_ids: set[str] = set()

    for product in ranked:
        category = str(product.get("category") or "Outros")
        if per_category[category] >= MAX_PER_CATEGORY:
            continue
        selected.append(product)
        selected_ids.add(str(product.get("id")))
        per_category[category] += 1
        if len(selected) >= MAX_POSTS:
            return selected

    for product in ranked:
        item_id = str(product.get("id"))
        if item_id in selected_ids:
            continue
        selected.append(product)
        if len(selected) >= MAX_POSTS:
            break
    return selected


def build_entry(product: dict, position: int) -> dict:
    price = money(product.get("price"))
    discount = round(discount_value(product))
    discount_line = f"\n🔥 {discount}% OFF" if discount > 0 else ""
    caption = (
        f"Achado #{position}: {product['name']}\n"
        f"💰 {price}{discount_line}\n"
        f"👉 {product['affiliateUrl']}\n\n"
        "Preço e disponibilidade podem mudar. Confira no Mercado Livre."
    )
    story = f"ACHADO DO DIA\n{product['name']}\n{price}"
    if discount > 0:
        story += f"\n{discount}% OFF"
    story += "\nLink na oferta"
    return {
        "position": position,
        "id": product.get("id"),
        "name": product.get("name"),
        "category": product.get("category"),
        "price": product.get("price"),
        "oldPrice": product.get("oldPrice"),
        "discount": discount or None,
        "affiliateUrl": product.get("affiliateUrl"),
        "imageUrl": product.get("imageUrl"),
        "caption": caption,
        "storyText": story,
    }


def main() -> int:
    data = load_catalog()
    selected = choose(data.get("products", []))
    entries = [build_entry(product, i) for i, product in enumerate(selected, start=1)]
    payload = {
        "sourceCollectedAt": data.get("collectedAt"),
        "generatedFrom": "catálogo atual MiraDesconto",
        "count": len(entries),
        "selectionPolicy": "verified-price-within-24h-and-confirmed-availability",
        "posts": entries,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Pauta automática — MiraDesconto",
        "",
        f"Catálogo-base: {data.get('collectedAt') or 'data não informada'}",
        "",
        "Somente preços verificados nas últimas 24 horas e disponibilidade confirmada são elegíveis. Seleção automática com variedade de categorias. Confirme a oferta antes de publicar, pois preço e estoque podem mudar.",
        "",
    ]
    for entry in entries:
        lines.extend([
            f"## {entry['position']}. {entry['name']}",
            "",
            f"**Categoria:** {entry['category'] or 'Outros'}  ",
            f"**Preço:** {money(entry['price'])}  ",
            f"**Desconto:** {str(entry['discount']) + '%' if entry['discount'] else 'não confirmado'}  ",
            f"**Imagem:** {entry['imageUrl']}  ",
            f"**Link afiliado:** {entry['affiliateUrl']}",
            "",
            "**Legenda pronta:**",
            "",
            entry['caption'],
            "",
            "**Texto curto para Story:**",
            "",
            entry['storyText'],
            "",
            "---",
            "",
        ])
    OUT_MD.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(json.dumps({"social_posts_generated": len(entries), "source": data.get("collectedAt")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
