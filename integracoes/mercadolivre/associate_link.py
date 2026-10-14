"""Associa link oficial ao anúncio exato, sempre por revisão antes de publicar.

O link deve redirecionar diretamente para a página inequívoca do MESMO item
e da mesma variação. Perfil social, lista e recomendações são recusados.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, build_opener

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "integracoes"))
from product_card import Unconfirmed, identity
from import_links import Redirects, affiliate, allowed
import catalogo

ARCHIVE = "links-afiliados.json"


def direct_destination(link, *, opener=None):
    """Retorna (item_id, variation_id) somente de uma página de anúncio real."""
    if not affiliate(link):
        raise ValueError("Link de afiliado não reconhecido")
    client = opener if opener is not None else build_opener(Redirects())
    with client.open(Request(link, headers={"User-Agent": "Mozilla/5.0",
                                          "Accept": "text/html"}), timeout=25) as response:
        final_url = response.geturl()
    if not allowed(final_url):
        raise ValueError("Destino fora do domínio oficial")
    path = urlsplit(final_url).path.lower()
    if "/social/" in path or "/lists/" in path:
        raise ValueError("Link de perfil ou lista não pode ser vinculado a um anúncio individual")
    # A product page is required; URL parameters on unrelated pages are not proof.
    if "/p/mlb" not in path and not re.search(r"/mlb-\d{7,}", path):
        raise ValueError("Destino não é uma página inequívoca de produto")
    try:
        return identity(final_url)
    except Unconfirmed:
        raise ValueError("Não foi possível confirmar o ID exato no destino") from None


def prepare(catalog, archive, item_id, link, destination, when):
    """Pura: não altera os objetos recebidos; prepara o cadastro e a procedência."""
    if not re.fullmatch(r"MLB\d{7,}", item_id or ""):
        raise ValueError("Informe o ID MLB completo do anúncio")
    if not affiliate(link):
        raise ValueError("Link de afiliado inválido")
    current = next((p for p in catalog["products"] if p["id"] == item_id), None)
    if current is None:
        raise ValueError("Produto ainda não está no catálogo")
    if destination[0] != item_id:
        raise ValueError("O link de afiliado aponta para outro anúncio")
    if current.get("itemId") not in (None, item_id):
        raise ValueError("ID de anúncio do cadastro difere; revisão manual necessária")
    try:
        expected = identity(current["productUrl"])
    except (KeyError, Unconfirmed):
        raise ValueError("Produto cadastrado não possui identidade verificável") from None
    if expected != destination:
        raise ValueError("O link não confirma a mesma variação do anúncio cadastrado")
    # Individual short links cannot be silently reused for other products.
    for row in archive:
        if row["id"] != item_id and row.get("affiliateUrl") == link:
            raise ValueError("Este link já está atribuído a outro produto")
    existing = next((row for row in archive if row["id"] == item_id), None)
    if current.get("affiliateUrl") == link:
        if existing is not None and existing.get("affiliateUrl") == link:
            return copy.deepcopy(catalog), copy.deepcopy(archive), False
        raise ValueError("Link existente não confere com o arquivo de procedência")
    if existing and current.get("affiliateUrl") != existing.get("affiliateUrl"):
        raise ValueError("O link existente difere do arquivo de procedência")

    updated = copy.deepcopy(catalog)
    records = copy.deepcopy(archive)
    item = next(p for p in updated["products"] if p["id"] == item_id)
    item["affiliateUrl"] = link
    item["affiliateLinkType"] = "product"
    # A price observed through a previous link cannot be presented as current.
    item.pop("priceCheck", None)
    item.pop("priceSource", None)
    # The item is temporarily removed from promotional display until fresh evidence.
    updated["publishedIds"] = [key for key in updated["publishedIds"] if key != item_id]
    item["featured"] = False

    stamp = when.astimezone(timezone.utc).isoformat(timespec="seconds")
    if existing:
        record = next(p for p in records if p["id"] == item_id)
        previous = record.pop("affiliateUrl", None)
        record.pop("fullAffiliateUrl", None)
        record["affiliateUrl"] = link
        record["previousAffiliateUrl"] = previous
        record["updatedAt"] = stamp
    else:
        records.append({"id": item_id, "productUrl": current["productUrl"],
                        "affiliateUrl": link, "generatedAt": when.date().isoformat(),
                        "updatedAt": stamp})
    # Keep remaining ranking positions consistent with the publishing invariant.
    for pos, visible_id in enumerate(updated["publishedIds"], 1):
        row = next(p for p in updated["products"] if p["id"] == visible_id)
        row["rank"] = pos
        row["featured"] = pos <= 12
    return updated, records, True


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--item-id", required=True)
    parser.add_argument("--affiliate-url", required=True)
    parser.add_argument("--apply", action="store_true",
                        help="Atualiza arquivos apenas na branch de revisão")
    args = parser.parse_args(argv)
    destination = direct_destination(args.affiliate_url)
    catalog = catalogo.load(ROOT)
    archive = catalogo.read_json(ROOT / ARCHIVE)
    updated, records, changed = prepare(
        catalog, archive, args.item_id, args.affiliate_url, destination,
        datetime.now(timezone.utc),
    )
    if not changed:
        print("Link já vinculado; nenhuma alteração necessária.")
        return 0
    with tempfile.TemporaryDirectory() as temp:
        temp_root = Path(temp)
        (temp_root / ARCHIVE).write_text(catalogo.dumps(records, pretty=True) + "\n",
                                          encoding="utf-8")
        rendered = catalogo.render(updated, temp_root)
    if args.apply:
        rendered[ARCHIVE] = catalogo.dumps(records, pretty=True) + "\n"
        rendered[catalogo.SOURCE.as_posix()] = catalogo.dumps(updated, pretty=True) + "\n"
        catalogo.write_files(rendered, ROOT)
        print("Branch atualizada para revisão. Nenhuma publicação automática.")
    else:
        print("Associação segura verificada em prévia. Use --apply apenas na branch de revisão.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        print("Operação recusada: " + str(error), file=sys.stderr)
        raise SystemExit(1)
