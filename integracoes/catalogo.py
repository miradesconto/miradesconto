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
                'affiliateUrl', 'imageUrl', 'rank', 'featured', 'available')
HEADER = '// Dados do catálogo; preços e status podem ser atualizados pela API oficial do Mercado Livre.\n'


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
    if len(published) < MIN_PRODUCTS:
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
    for position, item_id in enumerate(published, 1):
        p = by_id[item_id]
        price = p.get('price')
        if isinstance(price, bool) or not isinstance(price, (float, int)) or not math.isfinite(price) or price <= 0:
            raise ValueError(f'Preço inválido: {item_id}')
        old = p.get('oldPrice')
        if old is not None and (isinstance(old, bool) or not isinstance(old, (float, int)) or not math.isfinite(old) or old <= 0):
            raise ValueError(f'Preço anterior inválido: {item_id}')
        if not str(p.get('affiliateUrl', '')).startswith('https://meli.la/'):
            raise ValueError(f'Link ausente/inválido: {item_id}')
        if not str(p.get('imageUrl', '')).startswith(('http://', 'https://')):
            raise ValueError(f'Imagem ausente/inválida: {item_id}')
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
        old = by_id.get(p['id'])
        if old is None:
            raise ValueError('Cadastre o produto antes de publicar: ' + p['id'])
        for key in ('affiliateUrl', 'imageUrl'):
            if p.get(key) != old.get(key):
                raise ValueError(f"Coleta tentou alterar {key}: {p['id']}")
        by_id[p['id']] = copy.deepcopy(p)
    catalog['products'] = [by_id[p['id']] for p in catalog['products']]
    catalog['publishedIds'] = incoming_ids
    catalog['metadata'] = {k: copy.deepcopy(v) for k, v in data.items() if k != 'products'}
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
