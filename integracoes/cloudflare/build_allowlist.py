"""Empacota somente identidade/variação dos anúncios publicados, sem preços/links."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "integracoes"))
from mercadolivre.product_card import identity

data = json.loads((ROOT / "dados/catalogo.json").read_text(encoding="utf-8"))
registered = {p["id"]: p for p in data["products"]}
allowed = {}
for item_id in data["publishedIds"]:
    if not re.fullmatch(r"MLB\d{7,14}", item_id) or item_id in allowed:
        raise ValueError("ID inválido/duplicado no catálogo publicado")
    p = registered[item_id]
    # Nunca trocar o anúncio por um vencedor do catálogo de outro vendedor.
    # A opção observada no cartão não vincula uma URL sem opção explícita.
    variation = p.get("variationId")
    if variation is None:
        variation = identity(p.get("productUrl", ""))[1]
    if variation is not None and not re.fullmatch(r"\d{1,20}", str(variation)):
        raise ValueError("Variação inválida: " + item_id)
    allowed[item_id] = str(variation) if variation is not None else None
if not allowed:
    raise ValueError("Catálogo publicado vazio")
target = Path(__file__).with_name("allowed-items.json")
target.write_text(json.dumps(allowed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Allowlist gerada: {len(allowed)} anúncios publicados")
