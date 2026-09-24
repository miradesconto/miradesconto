#!/usr/bin/env python3
"""Refresh the existing catalog from exact product cards on affiliate pages.

The seller sale_price API returns 403 for third-party affiliate listings. An
unconfirmed product keeps its previous price evidence and published position.
"""
from __future__ import annotations

import sys
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'integracoes'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import catalogo
from rebuild_catalog import refresh_one


def update(current, timestamp, workers=10, rotate=False):
    products = current['products']
    published = set(current['publishedIds'])
    # Keep unpublished products, all affiliate URLs, and the editorial ordering.
    candidates = [(index, product) for index, product in enumerate(products)
                  if rotate or product['id'] in published]
    result = dict(current)
    result['products'] = list(products)
    confirmed = changed = 0
    fresh_ids = set()
    failures = Counter()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(refresh_one, product, timestamp.isoformat(timespec='seconds')): index
                   for index, product in candidates}
        for future in as_completed(futures):
            index = futures[future]
            try:
                fresh, error = future.result()
            except Exception as exc:
                fresh, error = None, {'reason': type(exc).__name__}
            if fresh is None:
                failures[(error or {}).get('reason', 'unconfirmed')] += 1
                continue
            confirmed += 1
            fresh_ids.add(fresh['id'])
            changed += fresh != products[index]
            result['products'][index] = fresh
    print(f'Cartões exatos confirmados: {confirmed}/{len(candidates)}; alterados: {changed}; falhas: {dict(failures)}')
    if not confirmed:
        raise RuntimeError('Nenhum preço confirmado; catálogo preservado')
    metadata = dict(current['metadata'])
    if rotate:
        # Only rotate registered affiliate links with a price verified in this run.
        previous = list(current['publishedIds'])
        cursor = int(metadata.get('rotationCursor', -1))
        if cursor < -1 or cursor >= len(products):
            cursor = -1
        eligible = [i for i in list(range(cursor + 1, len(products))) + list(range(cursor + 1))
                    if products[i]['id'] not in published and products[i]['id'] in fresh_ids]
        newcomers = eligible[:min(20, max(0, len(previous) - 12))]
        if newcomers:
            # Refresh three visible featured slots and spread the rest through the catalog.
            cycle = int(metadata.get('rotationCycle', 0))
            slots = list(range(9, min(12, len(previous))))
            remaining = len(newcomers) - len(slots)
            start = 12 + (cycle * 17) % max(1, len(previous) - 12)
            slots.extend(12 + (start - 12 + offset) % (len(previous) - 12)
                         for offset in range(max(0, remaining)))
            for slot, index in zip(slots, newcomers):
                previous[slot] = products[index]['id']
            result['publishedIds'] = previous
            metadata['rotationCursor'] = newcomers[-1]
            metadata['rotationCycle'] = cycle + 1
            index_by_id = {item['id']: i for i, item in enumerate(products)}
            for rank, item_id in enumerate(previous, 1):
                row = index_by_id[item_id]
                result['products'][row] = dict(result['products'][row], rank=rank, featured=rank <= 12)
            print(f'Rotação: {len(newcomers)} produtos verificados entraram na vitrine')
    metadata['collectedAt'] = timestamp.strftime('%d/%m/%Y')
    metadata['apiSync'] = {
        'source': 'Mercado Livre — páginas públicas de afiliados',
        'updatedAt': timestamp.isoformat(timespec='seconds'),
        'strategy': 'exact-product-card-v1',
        'linksChecked': len(candidates),
        'pricesConfirmed': confirmed,
    }
    result['metadata'] = metadata
    return result, changed + (result['publishedIds'] != current['publishedIds'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--rotate', action='store_true', help='Alternar até 20 produtos cadastrados e verificados')
    args = parser.parse_args()
    current = catalogo.load(ROOT)
    updated, changed = update(current, datetime.now(timezone.utc), rotate=args.rotate)
    if not changed:
        print('Nenhuma mudança confirmada no catálogo')
        return
    files = catalogo.render(updated, ROOT)
    files[catalogo.SOURCE.as_posix()] = catalogo.dumps(updated, pretty=True) + '\n'
    catalogo.write_files(files, ROOT)


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, ValueError) as exc:
        print(f'ERRO: {exc}', file=sys.stderr)
        raise SystemExit(1)
