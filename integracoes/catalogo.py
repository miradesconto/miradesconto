"""Cadastro principal e geração determinística, sem rede ou credenciais."""
from __future__ import annotations

import argparse
import copy
import json
import math
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('dados/catalogo.json')
MIN_PRODUCTS = 450
COMPACT_KEYS = ('id', 'name', 'category', 'price', 'oldPrice', 'discount',
                'affiliateUrl', 'offerUrl', 'imageUrl', 'itemId', 'catalogProductId', 'lastUpdated', 'rank', 'featured', 'available', 'priceCheck', 'availabilityStatus')
HEADER = '// Dados do catálogo; preços e status podem ser atualizados pela API oficial do Mercado Livre.\n'


def exact_offer_url(product):
    """Use the unchanged tracked product URL collected from the owner's list."""
    from urllib.parse import urlsplit, parse_qs
    from uuid import UUID
    try:
        url = urlsplit(product.get('productUrl', ''))
        query = parse_qs(url.query)
        fragment = parse_qs(url.fragment)
        item = query.get('wid', fragment.get('wid', []))
        tool = query.get('matt_tool_id', fragment.get('matt_tool_id', []))
        tracking = query.get('tracking_id', fragment.get('tracking_id', []))
        list_source = query.get('source', fragment.get('source', [])) == ['lists']
        list_tracking = False
        if p_source := product.get('registrationSource'):
            if p_source == 'affiliate-panel' and list_source and len(tracking) == 1:
                UUID(tracking[0])
                list_tracking = True
        if (url.scheme == 'https' and url.hostname in ('www.mercadolivre.com.br', 'mercadolivre.com.br')
                and item == [product['id']] and ((len(tool) == 1 and tool[0].isdigit()) or list_tracking)):
            return product['productUrl']
    except (ValueError, KeyError, TypeError):
        pass
    return None


def dumps(value, *, pretty=False):
    return json.dumps(value, ensure_ascii=False, allow_nan=False,
                      indent=2 if pretty else None,
                      separators=None if pretty else (',', ':'))


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def validate(catalog, root=ROOT):
    if catalog.get('schemaVersion') != 1:
        raise ValueError('Versão de cadastro não suportada')
    products = catalog.get('products')
    published = catalog.get('publishedIds')
    if not isinstance(products, list) or not isinstance(published, list):
        raise ValueError('Cadastro precisa de products e publishedIds')
    ids = []
    for p in products:
        if not isinstance(p, dict) or not re.fullmatch(r'MLB\d{7,}', str(p.get('id', ''))):
            raise ValueError('ID inválido no cadastro')
        if not isinstance(p.get('name'), str) or not p['name'].strip():
            raise ValueError(f"Nome ausente: {p['id']}")
        ids.append(p['id'])
    if len(ids) != len(set(ids)) or len(published) != len(set(published)):
        raise ValueError('IDs duplicados')
    by_id = dict(zip(ids, products))
    if not set(published).issubset(by_id):
        raise ValueError('Vitrine contém ID fora do cadastro')
    if catalog.get('metadata', {}).get('niche') != 'tech' and len(published) < MIN_PRODUCTS:
        raise ValueError(f'Vitrine abaixo do mínimo de {MIN_PRODUCTS} produtos')
    if not isinstance(catalog.get('metadata'), dict) or 'products' in catalog['metadata']:
        raise ValueError('Metadados inválidos')
    if catalog.get('featuredPolicy') != 'first-12-published':
        raise ValueError('Política de destaques não suportada')
    archive = read_json(root / 'links-afiliados.json')
    approved = {p['id']: p.get('affiliateUrl') for p in archive}
    for p in products:
        link = p.get('affiliateUrl')
        if link and link != approved.get(p['id']):
            raise ValueError(f"Link difere do registro de afiliados: {p['id']}")
    from tech_policy import eligible
    for position, item_id in enumerate(published, 1):
        if catalog['metadata'].get('niche') == 'tech' and not eligible(by_id[item_id]):
            raise ValueError('Produto fora da política tech: ' + item_id)
        p = by_id[item_id]
        price = p.get('price')
        if isinstance(price, bool) or not isinstance(price, (float, int)) or not math.isfinite(price) or price <= 0:
            raise ValueError(f'Preço inválido: {item_id}')
        old = p.get('oldPrice')
        if old is not None and (isinstance(old, bool) or not isinstance(old, (float, int)) or not math.isfinite(old) or old <= 0):
            raise ValueError(f'Preço anterior inválido: {item_id}')
        if not re.fullmatch(r'https://(?:meli\.la/[A-Za-z0-9]+|(?:www\.)?mercadolivre\.com(?:\.br)?/sec/[A-Za-z0-9]+)', str(p.get('affiliateUrl', ''))):
            raise ValueError(f'Link ausente/inválido: {item_id}')
        if not str(p.get('imageUrl', '')).startswith(('http://', 'https://')):
            raise ValueError(f'Imagem ausente/inválida: {item_id}')
        evidence = p.get('priceCheck')
        if evidence is not None:
            from datetime import datetime
            from qualidade import usable_price
            try:
                checked = datetime.fromisoformat(evidence['checkedAt'].replace('Z', '+00:00'))
            except (KeyError, TypeError, ValueError, AttributeError):
                raise ValueError(f'Evidência de preço inválida: {item_id}')
            if not usable_price(p, checked):
                raise ValueError(f'Evidência de preço divergente: {item_id}')
            if p.get('availabilityStatus') != 'unknown' or p.get('available') is not None:
                raise ValueError(f'Cartão de preço não confirma estoque: {item_id}')
        if p.get('rank') != position or p.get('featured') is not (position <= 12):
            raise ValueError(f'Ranking/destaque divergente: {item_id}')
    # Also reject NaN in fields outside the price validation.
    dumps(catalog)


def load(root=ROOT):
    catalog = read_json(root / SOURCE)
    validate(catalog, root)
    return catalog


def public_data(catalog):
    by_id = {p['id']: p for p in catalog['products']}
    data = copy.deepcopy(catalog['metadata'])
    # Preserve the original public key order (including products before apiSync).
    sync = data.pop('apiSync', None)
    data['products'] = [copy.deepcopy(by_id[i]) for i in catalog['publishedIds']]
    counts = {}
    for p in data['products']:
        counts[p.get('affiliateUrl')] = counts.get(p.get('affiliateUrl'), 0) + 1
    for p in data['products']:
        p.pop('offerUrl', None)
        # Individual short links stay intact. Shared lists need an exact tracked destination.
        if p.get('affiliateUrl') == 'https://meli.la/1NguveN' or p.get('affiliateUrl') in data.get('affiliateSources', []) or counts.get(p.get('affiliateUrl'), 0) > 1:
            destination = exact_offer_url(p)
            if destination:
                p['offerUrl'] = destination
    if sync is not None:
        data['apiSync'] = sync
    return data


def render(catalog, root=ROOT):
    validate(catalog, root)
    data = public_data(catalog)
    products = data['products']
    files = {'produtos.js': HEADER + 'window.MIRA_DATA = ' + dumps(data) + ';\n'}
    for start in range(0, len(products), 100):
        rows = [{k: p[k] for k in COMPACT_KEYS if k in p} for p in products[start:start + 100]]
        files[f'catalogo/produtos-{start // 100 + 1:03d}.json'] = dumps(rows) + '\n'
    editorial = {p['id']: {'name': p.get('name'), 'imageUrl': p.get('imageUrl'),
                          'available': p.get('available', True) is not False} for p in products}
    files['_data/produtos.json'] = dumps(editorial, pretty=True) + '\n'
    return files


def check(root=ROOT):
    files = render(load(root), root)
    errors = [name for name, text in files.items()
              if not (root / name).exists() or (root / name).read_text(encoding='utf-8') != text]
    errors.extend(p.relative_to(root).as_posix() for p in (root / 'catalogo').glob('produtos-*.json')
                  if p.relative_to(root).as_posix() not in files)
    if errors:
        raise ValueError('Arquivos gerados divergentes: ' + ', '.join(errors))
    return len(load(root)['publishedIds'])


def write_files(files, root):
    # Validate/render before entering here. Each replacement is atomic; Git is
    # the transaction boundary for publishing the complete set to Pages.
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + '.tmp')
        tmp.write_bytes(text.encode('utf-8'))
        os.replace(tmp, path)
    for path in (root / 'catalogo').glob('produtos-*.json'):
        if path.relative_to(root).as_posix() not in files:
            path.unlink()


def generate(root=ROOT, output=None):
    files = render(load(root), root)
    write_files(files, output or root)


def apply_snapshot(data, root=ROOT):
    """Merge observed products without deleting registered products on failures."""
    catalog = load(root)
    by_id = {p['id']: p for p in catalog['products']}
    incoming = data['products']
    incoming_ids = [p['id'] for p in incoming]
    if len(incoming_ids) != len(set(incoming_ids)):
        raise ValueError('Snapshot contém IDs duplicados')
    for p in incoming:
        price = p.get('price')
        if isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 0:
            raise ValueError('Preço inválido no snapshot: ' + str(p.get('id')))
        old = by_id.get(p['id'])
        if old is None:
            raise ValueError('Cadastre o produto antes de publicar: ' + p['id'])
        for key in ('affiliateUrl', 'imageUrl'):
            if p.get(key) != old.get(key):
                raise ValueError(f"Coleta tentou alterar {key}: {p['id']}")
        by_id[p['id']] = copy.deepcopy(p)
        by_id[p['id']].pop('offerUrl', None)  # Derived destination, never a source override.
    catalog['products'] = [by_id[p['id']] for p in catalog['products']]
    catalog['publishedIds'] = incoming_ids
    policy = {k: catalog['metadata'][k] for k in ('niche', 'discountBasis') if k in catalog['metadata']}
    catalog['metadata'] = {k: copy.deepcopy(v) for k, v in data.items() if k != 'products'}
    catalog['metadata'].update(policy)
    from tech_policy import reconcile
    reconcile(catalog)
    files = render(catalog, root)
    files[SOURCE.as_posix()] = dumps(catalog, pretty=True) + '\n'
    write_files(files, root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['check', 'generate', 'organize'])
    parser.add_argument('--output', type=Path, help='Prévia: grava derivados nesta pasta, preservando o cadastro')
    args = parser.parse_args()
    if args.command == 'check':
        print(f'OK: {check()} produtos; cadastro e derivados consistentes')
    elif args.command == 'organize':
        # Node supplies only reviewed categories, never prices, links or images.
        import sys
        categories = json.load(sys.stdin)
        catalog = load()
        if set(categories) != {p['id'] for p in catalog['products']}:
            raise ValueError('Classificação deve cobrir o cadastro completo')
        for p in catalog['products']:
            if not isinstance(categories[p['id']], str) or not categories[p['id']].strip():
                raise ValueError('Categoria inválida')
            p['category'] = categories[p['id']]
        files = render(catalog)
        files[SOURCE.as_posix()] = dumps(catalog, pretty=True) + '\n'
        write_files(files, ROOT)
    else:
        generate(output=args.output)


if __name__ == '__main__':
    main()
