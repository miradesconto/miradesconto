#!/usr/bin/env python3
"""Refresh the existing catalog from exact product cards on affiliate pages.

The seller sale_price API returns 403 for third-party affiliate listings. An
unconfirmed product keeps its previous price evidence and published position.
"""
from __future__ import annotations

import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'integracoes'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import catalogo
from rebuild_catalog import refresh_one


def update(current, timestamp, workers=10):
    products = current['products']
    published = set(current['publishedIds'])
    # Keep unpublished products, all affiliate URLs, and the editorial ordering.
    candidates = [(index, product) for index, product in enumerate(products)
                  if product['id'] in published]
    result = dict(current)
    result['products'] = list(products)
    confirmed = changed = 0
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
            changed += fresh != products[index]
            result['products'][index] = fresh
    print(f'Cartões exatos confirmados: {confirmed}/{len(candidates)}; alterados: {changed}; falhas: {dict(failures)}')
    if not confirmed:
        raise RuntimeError('Nenhum preço confirmado; catálogo preservado')
    metadata = dict(current['metadata'])
    metadata['collectedAt'] = timestamp.strftime('%d/%m/%Y')
    metadata['apiSync'] = {
        'source': 'Mercado Livre — páginas públicas de afiliados',
        'updatedAt': timestamp.isoformat(timespec='seconds'),
        'strategy': 'exact-product-card-v1',
        'linksChecked': len(candidates),
        'pricesConfirmed': confirmed,
    }
    result['metadata'] = metadata
    return result, changed


def main():
    current = catalogo.load(ROOT)
    updated, changed = update(current, datetime.now(timezone.utc))
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
