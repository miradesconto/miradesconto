#!/usr/bin/env python3
"""Register new affiliate products after confirming their exact public card.

Input is a JSON array with id, name, category, productUrl, imageUrl and
affiliateUrl. The affiliate short URL must originate in the owner's portal.
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

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'integracoes'))
from product_card import identity, Unconfirmed
from rebuild_catalog import refresh_one
import catalogo

ARCHIVE = Path('links-afiliados.json')
FIELDS = ('id', 'name', 'category', 'productUrl', 'imageUrl', 'affiliateUrl')


def prepare(catalog, archive, entries, timestamp, refresh=refresh_one):
    if not isinstance(entries, list) or not entries:
        raise ValueError('O arquivo precisa conter uma lista de produtos')
    updated = copy.deepcopy(catalog)
    approved = copy.deepcopy(archive)
    known_ids = {p['id'] for p in catalog['products']}
    known_links = {p.get('affiliateUrl') for p in archive}
    categories = {p['category'] for p in catalog['products']}
    for entry in entries:
        if not isinstance(entry, dict) or any(not isinstance(entry.get(k), str) or not entry[k].strip() for k in FIELDS):
            raise ValueError('Cada produto precisa de: ' + ', '.join(FIELDS))
        item_id = entry['id'].strip().upper().replace('-', '')
        if not re.fullmatch(r'MLB\d{7,}', item_id) or item_id in known_ids:
            raise ValueError(f'ID inválido ou já cadastrado: {item_id}')
        affiliate = entry['affiliateUrl'].strip()
        if not re.fullmatch(r'https://meli\.la/[A-Za-z0-9]+', affiliate) or affiliate in known_links:
            raise ValueError(f'Link de afiliado inválido ou repetido: {item_id}')
        product_url = entry['productUrl'].strip()
        try:
            linked_id, _ = identity(product_url)
        except Unconfirmed:
            raise ValueError(f'URL do produto sem ID de anúncio verificável: {item_id}') from None
        if linked_id != item_id:
            raise ValueError(f'URL do produto aponta para outro anúncio: {item_id}')
        image = urlsplit(entry['imageUrl'].strip())
        if image.scheme != 'https' or not image.hostname or not image.hostname.endswith('.mlstatic.com'):
            raise ValueError(f'Imagem deve ser do Mercado Livre: {item_id}')
        category = entry['category'].strip()
        if category not in categories:
            raise ValueError(f'Categoria não cadastrada: {category}')
        name = entry['name'].strip()
        if len(name) > 180:
            raise ValueError(f'Nome longo demais: {item_id}')
        candidate = dict(id=item_id, name=name, category=category,
                         productUrl=product_url, imageUrl=entry['imageUrl'].strip(),
                         affiliateUrl=affiliate, rank=len(updated['products']) + 1,
                         featured=False)
        verified, error = refresh(candidate, timestamp.isoformat(timespec='seconds'))
        if verified is None:
            raise ValueError(f'Preço não confirmado para {item_id}: {(error or {}).get("reason", "sem cartão exato")}')
        updated['products'].append(verified)
        approved.append(dict(id=item_id, productUrl=product_url, affiliateUrl=affiliate,
                             generatedAt=timestamp.date().isoformat()))
        known_ids.add(item_id)
        known_links.add(affiliate)
    return updated, approved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path, help='JSON com produtos e links gerados no Portal de Afiliados')
    parser.add_argument('--apply', action='store_true', help='Gravar após validação; sem esta opção apenas confere')
    args = parser.parse_args()
    entries = json.loads(args.input.read_text(encoding='utf-8'))
    current = catalogo.load(ROOT)
    archive = catalogo.read_json(ROOT / ARCHIVE)
    updated, approved = prepare(current, archive, entries, datetime.now(timezone.utc))
    # Validate against the proposed affiliate registry before touching the repository.
    with tempfile.TemporaryDirectory() as tmp:
        check = Path(tmp)
        (check / ARCHIVE).write_text(catalogo.dumps(approved, pretty=True) + '\n', encoding='utf-8')
        catalogo.validate(updated, check)
    count = len(updated['products']) - len(current['products'])
    print(f'{count} produtos novos com preço e link verificados; vitrine atual preservada')
    if not args.apply:
        print('Prévia concluída. Execute novamente com --apply para cadastrar.')
        return
    # Source and affiliate registry are committed together; publication requires
    # the whole Git transaction to succeed.
    (ROOT / ARCHIVE).write_text(catalogo.dumps(approved, pretty=True) + '\n', encoding='utf-8')
    (ROOT / catalogo.SOURCE).write_text(catalogo.dumps(updated, pretty=True) + '\n', encoding='utf-8')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f'ERRO: {exc}', file=sys.stderr)
        raise SystemExit(1)
