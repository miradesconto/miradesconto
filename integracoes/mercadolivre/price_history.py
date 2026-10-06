#!/usr/bin/env python3
"""Archive verified observations; never infer missing prices or dates."""
import argparse
import json
import math
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
METHODS = {'poly-card-v1', 'ml-sale-price-v1'}

def observation(p, now):
    e = p.get('priceCheck') or {}
    expected = p.get('itemId') if e.get('method') == 'ml-sale-price-v1' else p.get('id')
    price = p.get('price')
    if e.get('status') != 'verified' or e.get('method') not in METHODS or e.get('currency') != 'BRL': return None
    if not expected or e.get('itemId') != expected or e.get('price') != price or e.get('oldPrice') != p.get('oldPrice'): return None
    if isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 0 or p.get('available') is False: return None
    try:
        date = datetime.fromisoformat(e['checkedAt'].replace('Z', '+00:00'))
        if date.tzinfo is None or date > now or date < now - timedelta(days=180): return None
    except (KeyError, ValueError, TypeError): return None
    return {'at': date.astimezone(timezone.utc).isoformat(timespec='seconds'), 'price': price,
            'reference': p.get('oldPrice'), 'itemId': expected, 'variationId': e.get('variationId'), 'method': e['method']}

def archive(backfill=False, root=ROOT, now=None):
    now = now or datetime.now(timezone.utc)
    snapshots = [json.loads((root / 'dados/catalogo.json').read_text())]
    if backfill:
        refs = subprocess.check_output(['git', 'log', '--format=%H', '--since=180 days ago', '--', 'dados/catalogo.json'], cwd=root, text=True).splitlines()
        for ref in refs:
            try: snapshots.append(json.loads(subprocess.check_output(['git', 'show', ref + ':dados/catalogo.json'], cwd=root, text=True)))
            except (subprocess.CalledProcessError, ValueError): continue
    folder = root / 'historico'
    folder.mkdir(exist_ok=True)
    records = {}
    for snapshot in reversed(snapshots):
        for p in snapshot.get('products', []):
            row = observation(p, now)
            key = str(p.get('id', ''))
            if row and key.startswith('MLB') and key[3:].isdigit(): records.setdefault(key, []).append(row)
    count = 0
    for key, rows in records.items():
        path = folder / (key + '.json')
        previous = json.loads(path.read_text()).get('observations', []) if path.exists() else []
        unique = {(r['at'], r['itemId'], str(r.get('variationId'))): r for r in previous + rows
                  if datetime.fromisoformat(r['at']) >= now - timedelta(days=180)}
        data = {'productId': key, 'currency': 'BRL', 'observations': sorted(unique.values(), key=lambda r: r['at'])}
        content = json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n'
        if not path.exists() or path.read_text() != content:
            path.write_text(content); count += 1
    print(f'Histórico: {count} arquivos atualizados; {len(records)} anúncios com evidência válida')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--backfill', action='store_true')
    archive(parser.parse_args().backfill)
