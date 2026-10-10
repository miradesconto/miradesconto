#!/usr/bin/env python3
"""Publica observações verificadas no Worker/KV; não cria históricos locais."""
from __future__ import annotations
import argparse
import json
import math
import os
from pathlib import Path
import re
import subprocess
import time
from datetime import datetime, timezone, timedelta
from urllib.parse import urlsplit
import requests

ROOT = Path(__file__).resolve().parents[2]
METHODS = {'poly-card-v1', 'ml-sale-price-v1', 'ml-edge-item-v1'}
ID = re.compile(r'MLB\d{7,14}')


def normalized_row(row, now):
    if not isinstance(row, dict): raise ValueError('Registro histórico inválido')
    price, reference, variation = row.get('price'), row.get('reference'), row.get('variationId')
    def positive(n):
        return not isinstance(n, bool) and isinstance(n, (int, float)) and math.isfinite(n) and n > 0
    if (not positive(price) or (reference is not None and not positive(reference))
            or not ID.fullmatch(str(row.get('itemId', ''))) or row.get('method') not in METHODS
            or (variation is not None and not re.fullmatch(r'\d{1,20}', str(variation)))):
        raise ValueError('Preço, anúncio, método ou variação inválidos')
    try: at = datetime.fromisoformat(row['at'].replace('Z', '+00:00'))
    except (KeyError, AttributeError, ValueError, TypeError): raise ValueError('Data inválida') from None
    if at.tzinfo is None or at > now: raise ValueError('Data ausente/futura')
    if at < now - timedelta(days=180): return None
    return {'at': at.astimezone(timezone.utc).isoformat(timespec='seconds'), 'price': price,
            'reference': reference, 'itemId': row['itemId'],
            'variationId': str(variation) if variation is not None else None, 'method': row['method']}


def observation(p, now):
    e = p.get('priceCheck') or {}
    expected = p.get('itemId') if e.get('method') == 'ml-sale-price-v1' else p.get('id')
    if (e.get('status') != 'verified' or e.get('currency') != 'BRL' or p.get('available') is False
            or not expected or e.get('itemId') != expected or e.get('price') != p.get('price')
            or e.get('oldPrice') != p.get('oldPrice')): return None
    try:
        return normalized_row({'at': e.get('checkedAt'), 'price': p.get('price'),
            'reference': p.get('oldPrice'), 'itemId': expected,
            'variationId': e.get('variationId'), 'method': e.get('method')}, now)
    except ValueError: return None


def history_base(value):
    parsed = urlsplit(value or '')
    local = parsed.hostname in ('localhost', '127.0.0.1')
    if ((parsed.scheme != 'https' and not (local and parsed.scheme == 'http'))
            or not parsed.hostname or parsed.username or parsed.password
            or parsed.path not in ('', '/') or parsed.query or parsed.fragment):
        raise ValueError('MIRA_HISTORY_BASE_URL precisa ser uma origem HTTPS, sem path/query/credenciais')
    return value.rstrip('/')


class HistoryClient:
    def __init__(self, base=None, token=None, session=None, sleep=time.sleep):
        self.base = history_base(base if base is not None else os.getenv('MIRA_HISTORY_BASE_URL'))
        self.token = token if token is not None else os.getenv('MIRA_HISTORY_WRITE_TOKEN', '')
        if len(self.token) < 32: raise ValueError('Configure MIRA_HISTORY_WRITE_TOKEN nos secrets')
        self.session = session or requests.Session()
        self.sleep = sleep

    def post(self, product_id, rows, mode='normal'):
        if not ID.fullmatch(product_id): raise ValueError('ID inválido')
        payload = {'schemaVersion': 1, 'productId': product_id, 'currency': 'BRL',
                   'observations': rows, 'mode': mode}
        for attempt in range(3):
            try:
                response = self.session.post(self.base + '/api/history/ingest', json=payload,
                    headers={'Authorization': 'Bearer ' + self.token}, timeout=(5, 30), allow_redirects=False)
            except requests.RequestException:
                if attempt == 2: raise RuntimeError('Falha de rede no histórico; fonte local preservada') from None
                self.sleep(2 ** attempt); continue
            if response.status_code in (200, 202):
                try: data = response.json()
                except ValueError: raise RuntimeError('Resposta inválida do Worker') from None
                if data.get('saved') is not True or data.get('productId') != product_id:
                    raise RuntimeError('Worker não confirmou armazenamento do anúncio')
                if data.get('reason') in ('key_rate_limit', 'kv_error') and attempt < 2:
                    self.sleep(1.1 if data['reason'] == 'key_rate_limit' else 2 ** attempt); continue
                if data.get('reason') == 'kv_error': raise RuntimeError('KV indisponível; observações preservadas no coordenador')
                return data
            if response.status_code in (429, 500, 502, 503, 504) and attempt < 2:
                self.sleep(2 ** attempt); continue
            raise RuntimeError(f'Histórico recusado: HTTP {response.status_code}; fonte preservada')
        raise RuntimeError('Histórico sem confirmação')

    def read(self, product_id, verify=False):
        url = self.base + '/api/history/' + product_id + ('?verify=1' if verify else '')
        try:
            response = self.session.get(url, headers={'Authorization': 'Bearer ' + self.token} if verify else {},
                                        timeout=(5, 30), allow_redirects=False)
        except requests.RequestException: raise RuntimeError('Falha de leitura do histórico') from None
        if response.status_code != 200: raise RuntimeError(f'Histórico indisponível: HTTP {response.status_code}')
        try: value = response.json()
        except ValueError: raise RuntimeError('Histórico inválido') from None
        if value.get('productId') != product_id or value.get('currency') != 'BRL': raise RuntimeError('Identidade histórica divergente')
        return value


def archive(backfill=False, root=ROOT, now=None, client=None, migrate_local=False,
            cleanup_local=False, dry_run=False, all_products=False):
    if cleanup_local and not migrate_local: raise ValueError('--cleanup-local exige --migrate-local')
    now = now or datetime.now(timezone.utc)
    current = json.loads((root / 'dados/catalogo.json').read_text(encoding='utf-8'))
    selected = None if all_products or backfill else set(current.get('publishedIds', []))
    records, legacy = {}, {}
    def add(product_id, row):
        if not ID.fullmatch(product_id): raise ValueError('ID histórico inválido')
        key = (row['at'], row['itemId'], row['variationId'])
        bucket = records.setdefault(product_id, {})
        if key in bucket and bucket[key] != row: raise ValueError('Observações conflitantes: ' + product_id)
        bucket[key] = row
    def snapshot(value):
        for p in value.get('products', []):
            if selected is not None and p.get('id') not in selected: continue
            row = observation(p, now)
            if row: add(p['id'], row)
    if migrate_local:
        for path in sorted((root / 'historico').glob('*.json')):
            value = json.loads(path.read_text(encoding='utf-8'))
            product_id = value.get('productId')
            if (not ID.fullmatch(str(product_id or '')) or path.stem != product_id or value.get('currency') != 'BRL'
                    or value.get('schemaVersion',1) != 1):
                raise ValueError('Identidade histórica local divergente: ' + path.name)
            if not isinstance(value.get('observations'), list): raise ValueError('Histórico local inválido: ' + path.name)
            kept = []
            for row in value['observations']:
                row = normalized_row(row, now)
                if row: add(product_id, row); kept.append(row)
            legacy[product_id] = (path, kept)
            records.setdefault(product_id, {})
    if backfill:
        refs = subprocess.check_output(['git', 'log', '--format=%H', '--since=180 days ago', '--', 'dados/catalogo.json'], cwd=root, text=True).splitlines()
        for ref in reversed(refs):
            try: value = json.loads(subprocess.check_output(['git','show',ref+':dados/catalogo.json'],cwd=root,text=True))
            except (subprocess.CalledProcessError, ValueError): continue
            snapshot(value)
    snapshot(current)
    total = sum(len(rows) for rows in records.values())
    if dry_run:
        result = {'dryRun': True, 'products': len(records), 'observations': total, 'legacyFiles': len(legacy)}
        print(json.dumps(result)); return result
    client = client or HistoryClient()
    receipts, pending = {}, {}
    for product_id, values in sorted(records.items()):
        rows = sorted(values.values(), key=lambda row: (row['at'], row['itemId'], row['variationId'] or ''))
        if migrate_local or backfill:
            for offset in range(0, len(rows), 64): client.post(product_id, rows[offset:offset+64], mode='stage')
            receipt = client.post(product_id, [], mode='migration')
        else:
            receipt = client.post(product_id, rows)
        receipts[product_id] = receipt
        if not receipt.get('kvPublished'): pending[product_id] = receipt.get('reason', 'pending')
    if cleanup_local:
        for product_id, (path, rows) in legacy.items():
            if not receipts[product_id].get('kvPublished'): raise RuntimeError('Migração ainda pendente; nenhum arquivo removido')
            stored = client.read(product_id, verify=True)
            normalized = [normalized_row(row, now) for row in stored.get('observations', [])]
            lookup = {(r['at'],r['itemId'],r['variationId']):r for r in normalized if r}
            if any(lookup.get((r['at'],r['itemId'],r['variationId'])) != r for r in rows):
                raise RuntimeError('KV ainda não confirma todos os registros; nenhum arquivo removido')
        for path, _ in legacy.values(): path.unlink()
    result = {'savedProducts': len(receipts), 'observations': total, 'pendingPublication': len(pending),
              'pendingReasons': dict(sorted({reason: list(pending.values()).count(reason) for reason in set(pending.values())}.items())),
              'localFilesRemoved': len(legacy) if cleanup_local else 0}
    print(json.dumps(result)); return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ['backfill','migrate-local','cleanup-local','dry-run','all-products']:
        parser.add_argument('--'+flag, action='store_true')
    args = parser.parse_args()
    try: archive(**vars(args))
    except (ValueError, RuntimeError) as error: parser.exit(1, str(error)+'\n')
