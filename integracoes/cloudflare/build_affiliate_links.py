"""Empacota destinos oficiais por anúncio, sem inventar parâmetros de comissão."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "integracoes"))
from catalogo import exact_offer_url, public_data  # noqa: E402
from mercadolivre.product_card import identity  # noqa: E402


def split_destination(raw):
    """Preserva ordem, encoding, assinatura e fragmento byte a byte."""
    if not isinstance(raw, str) or not re.fullmatch(r"[\x21-\x7e]+", raw):
        raise ValueError("Destino contém espaços/caracteres inválidos")
    parsed = urlsplit(raw)
    if (parsed.scheme != "https" or parsed.username or parsed.password or parsed.port
            or parsed.hostname not in ("www.mercadolivre.com.br", "mercadolivre.com.br")):
        raise ValueError("Destino não é uma URL oficial HTTPS permitida")
    before_hash, marker, fragment = raw.partition("#")
    base, query_marker, query = before_hash.partition("?")
    return {"baseUrl": base, "search": query_marker + query, "hash": marker + fragment}


def build_registry(catalog, archive):
    policy = json.loads(Path(__file__).with_name("affiliate-policy.json").read_text(encoding="utf-8"))
    if not re.fullmatch(r"\d{1,20}", str(policy.get("toolId", ""))):
        raise ValueError("Identificação esperada de afiliado inválida")
    products = public_data(catalog)["products"]
    if not products or len({p["id"] for p in products}) != len(products):
        raise ValueError("Catálogo publicado vazio ou com IDs duplicados")
    archived = {}
    for p in archive:
        # O arquivo guarda campanhas anteriores para o mesmo anúncio.
        archived.setdefault(p["id"], []).append(p)
    counts = Counter(p.get("affiliateUrl") for p in products)
    generic = {"https://meli.la/1NguveN", *catalog.get("metadata", {}).get("affiliateSources", [])}
    registry = {}
    destinations = set()
    refs = set()
    for p in products:
        item_id = p["id"]
        if not re.fullmatch(r"MLB\d{7,14}", item_id):
            raise ValueError("ID de anúncio inválido")
        # A observação pode identificar uma opção selecionada sem que o link a fixe.
        # Somente a URL/configuração declarada vincula o destino; nunca inferir isso do preço.
        variation = p.get("variationId")
        if variation is None:
            variation = identity(p.get("offerUrl") or p.get("productUrl", ""))[1]
        variation = str(variation) if variation is not None else None
        if variation is not None and not re.fullmatch(r"\d{1,20}", variation):
            raise ValueError("Variação inválida: " + item_id)
        raw = p.get("offerUrl")
        if raw:
            if exact_offer_url(p) != raw or identity(raw) != (item_id, variation):
                raise ValueError("Destino de produto/rastreio divergente: " + item_id)
            kind = "tracked_product"
        else:
            matches = [old for old in archived.get(item_id, [])
                       if old.get("affiliateUrl") == p.get("affiliateUrl")]
            if len(matches) != 1:
                raise ValueError("Link oficial ausente ou ambíguo: " + item_id)
            old = matches[0]
            # Links de listas, compartilhados ou sem proveniência nunca são fallback.
            if (counts[p.get("affiliateUrl")] != 1 or p.get("affiliateUrl") in generic
                    or old.get("affiliateUrl") != p.get("affiliateUrl")):
                raise ValueError("Falta link oficial individual: " + item_id)
            if identity(old.get("productUrl", "")) != (item_id, variation):
                raise ValueError("Anúncio/variação do link oficial divergente: " + item_id)
            raw = old.get("fullAffiliateUrl", "")
            parsed = urlsplit(raw)
            q = parse_qs(parsed.query, keep_blank_values=True)
            if (not re.fullmatch(r"/social/[A-Za-z0-9_-]+", parsed.path) or parsed.fragment
                    or len(q.get("ref", [])) != 1 or not q["ref"][0]
                    or len(q.get("matt_tool", [])) != 1 or not q["matt_tool"][0].isdigit()
                    or len(q.get("matt_word", [])) != 1 or not q["matt_word"][0]):
                raise ValueError("Falta referência oficial individual: " + item_id)
            if q["ref"][0] in refs:
                raise ValueError("Referência oficial repetida entre anúncios")
            refs.add(q["ref"][0])
            kind = "signed_link"
        parts = split_destination(raw)
        parsed = urlsplit(raw)
        q, fragment = parse_qs(parsed.query), parse_qs(parsed.fragment)
        key = "matt_tool" if kind == "signed_link" else "matt_tool_id"
        tools = q.get(key, []) + fragment.get(key, [])
        if tools and tools != [policy["toolId"]]:
            raise ValueError("Identificação de afiliado de outra conta: " + item_id)
        if raw in destinations:
            raise ValueError("Destino compartilhado entre anúncios")
        destinations.add(raw)
        registry[item_id] = {"kind": kind, "variationId": variation, **parts}
    return registry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Confere sem modificar arquivos")
    args = parser.parse_args()
    data = json.loads((ROOT / "dados/catalogo.json").read_text(encoding="utf-8"))
    archive = json.loads((ROOT / "links-afiliados.json").read_text(encoding="utf-8"))
    registry = build_registry(data, archive)
    allowed = json.loads(Path(__file__).with_name("allowed-items.json").read_text(encoding="utf-8"))
    if allowed != {key: value["variationId"] for key, value in registry.items()}:
        raise ValueError("Regere build_allowlist.py antes dos destinos de afiliados")
    output = json.dumps(registry, ensure_ascii=False, indent=2) + "\n"
    target = Path(__file__).with_name("affiliate-links.json")
    if args.check:
        if not target.exists() or target.read_text(encoding="utf-8") != output:
            raise ValueError("Regere build_affiliate_links.py antes do deploy")
    else:
        target.write_text(output, encoding="utf-8")
    counts = Counter(p["kind"] for p in registry.values())
    print(f"Destinos oficiais {'verificados' if args.check else 'gerados'}: {len(registry)}; {dict(counts)}")


if __name__ == "__main__":
    main()
