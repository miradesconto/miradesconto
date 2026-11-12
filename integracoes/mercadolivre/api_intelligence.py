#!/usr/bin/env python3
"""Official read-only market signals and exact-item prices for the affiliate site.

No seller mutations, inferred affiliate links, stock promises or search-price claims.
Endpoint denials are recorded separately; one blocked feature cannot disable others.
"""
from __future__ import annotations
import copy
import json
import os
import re
import sys
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'integracoes'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import catalogo
from discover_candidates import Client as Transport, AccessError, canonical_product_link
from hourly_prices import Client as OAuthClient, AuthError, observe
from product_card import identity, Unconfirmed
from tech_policy import category

REPORT = ROOT / 'integracoes/mercadolivre/api-status.json'
SIGNALS = ROOT / '_data/mercadolivre_api.json'
ID = re.compile(r'MLB\d{7,}$')
USER_PRODUCT_ID = re.compile(r'MLBU\d{7,}$')
CATEGORY_ID = re.compile(r'MLB\d+$')
MAX_ITEMS = 40
MAX_CALLS = 110
RESTRICTED_RETRY_HOURS = 24  # A 403 is a permission decision, not a transient error.


def fresh(stamp, now, hours=24):
    try:
        dt = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
        return dt.tzinfo is not None and 0 <= (now - dt).total_seconds() <= hours * 3600
    except (AttributeError, ValueError, TypeError):
        return False


def normalized(text):
    return re.findall(r'[a-z0-9]+', unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode().lower())


def matched_trends(product, trends):
    words = set(normalized(product.get('name', '')))
    matches = []
    for row in trends:
        terms = normalized(row.get('keyword', ''))
        # Whole words prevent e.g. iPhone 15 matching iPhone 150; no fuzzy model claim.
        if len(terms) >= 2 and set(terms) <= words:
            matches.append(row['keyword'])
    return list(dict.fromkeys(matches))[:3]


class Client(OAuthClient):
    def __init__(self):
        self.token = os.getenv('ACCESS_TOKEN', '').strip()
        self.refreshed = False
        self.calls = 0
        self.started = time.monotonic()
        if not self.token:
            raise AuthError('ACCESS_TOKEN ausente')

    def get(self, path):
        for attempt in range(3):
            if self.calls >= MAX_CALLS or time.monotonic() - self.started > 240:
                raise RuntimeError('Orçamento de consultas atingido')
            self.calls += 1
            try:
                return Transport(self.token).get(path)
            except AccessError as exc:
                if exc.status == 401 and not self.refreshed:
                    required = ('CLIENT_ID', 'CLIENT_SECRET', 'REFRESH_TOKEN', 'GH_SECRETS_TOKEN')
                    if any(not os.getenv(k, '').strip() for k in required):
                        raise AuthError('Renovação OAuth requer configuração dos Secrets') from None
                    self.refresh()
                    continue
                if exc.status in (429, 500, 502, 503, 504) and attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise
        raise AuthError('Autenticação não confirmada')


class Probe:
    def __init__(self, client, report):
        self.client, self.report = client, report
        self.stopped = set()
        self.auth_failed = False

    def get(self, family, path):
        if family in self.stopped or self.auth_failed:
            return None
        row = self.report['capabilities'].setdefault(family, {'ok': 0, 'failed': 0, 'status': 'não comprovado'})
        try:
            data = self.client.get(path)
            row['ok'] += 1
            row['status'] = 'ok' if not row['failed'] else 'atenção'
            return data
        except AuthError:
            self.auth_failed = True
            row['status'] = 'requer intervenção'
            row['reason'] = 'oauth_renewal_required'
        except AccessError as exc:
            row['http'] = exc.status
            row['status'] = 'bloqueado' if exc.status in (401, 403) else 'atenção'
            if exc.status == 403:
                row['reason'] = 'permission_or_policy_restriction'
                row['lastAttemptAt'] = self.report.get('generatedAt') or datetime.now(timezone.utc).isoformat(timespec='seconds')
            if exc.status in (401, 403, 429):
                self.stopped.add(family)
            if exc.status == 401:
                self.auth_failed = True
        except (ValueError, RuntimeError, TypeError):
            row['status'] = 'atenção'
            row['reason'] = 'response_or_connection_unconfirmed'
            self.stopped.add(family)
        row['failed'] += 1
        return None


def remember_restricted_families(previous_report, report, probe, now):
    """Avoid retrying a policy-denied endpoint on every 15-minute sync.

    A family is probed again after 24h. This does not change ML permissions;
    report retains the denial and its original timestamp throughout the cooldown.
    Manual diagnostics deliberately bypass this cooldown.
    """
    if not isinstance(previous_report, dict):
        return
    for family in ('items', 'sale_price'):
        prior = (previous_report.get('capabilities') or {}).get(family)
        if not isinstance(prior, dict) or prior.get('http') != 403:
            continue
        last = prior.get('lastAttemptAt') or previous_report.get('generatedAt')
        if not fresh(last, now, RESTRICTED_RETRY_HOURS):
            continue
        checked = datetime.fromisoformat(last.replace('Z', '+00:00'))
        report['capabilities'][family] = {
            'status': 'bloqueado', 'http': 403,
            'reason': 'permission_or_policy_restriction',
            'lastAttemptAt': last,
            'nextRetryAt': (checked + timedelta(hours=RESTRICTED_RETRY_HOURS)).isoformat(),
            'cached': True,
        }
        probe.stopped.add(family)


def safe_text(value, maximum=160):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        return None
    if any(ord(c) < 32 for c in value):
        return None
    return value.strip()


def ranking_entry(entry, category_id, stamp):
    """Validate ITEM, PRODUCT and USER_PRODUCT rankings without inventing a rank."""
    if not isinstance(entry, dict):
        return None
    kind = entry.get('type')
    matcher = USER_PRODUCT_ID if kind == 'USER_PRODUCT' else ID if kind in ('ITEM', 'PRODUCT') else None
    item_id = entry.get('id')
    if matcher is None or not matcher.fullmatch(str(item_id)):
        return None
    position = entry.get('position')
    if position is not None and (type(position) is not int or not 1 <= position <= 20):
        return None
    return {'id': item_id, 'type': kind, 'position': position,
            'categoryId': category_id, 'checkedAt': stamp}


def item_metadata(product, item, stamp):
    if (not isinstance(item, dict) or item.get('id') != product['id']
            or item.get('site_id') != 'MLB' or item.get('currency_id') != 'BRL'
            or not canonical_product_link(item.get('permalink'), product['id'])):
        return None
    attrs = {}
    for attr in (item.get('attributes') or []):
        if isinstance(attr, dict) and attr.get('id') in ('BRAND', 'MODEL', 'RAM', 'INTERNAL_MEMORY', 'PROCESSOR_MODEL', 'SCREEN_SIZE'):
            value = safe_text(attr.get('value_name'))
            if value:
                attrs[attr['id']] = value
    status = item.get('status')
    return {'id': product['id'], 'checkedAt': stamp,
            'listingStatus': status if status in ('active', 'paused', 'closed', 'under_review', 'inactive') else 'unknown',
            'categoryId': item.get('category_id') if CATEGORY_ID.fullmatch(str(item.get('category_id'))) else None,
            'attributes': attrs, 'stockConfirmed': False}


def exact_unvaried(product, item):
    if item.get('status') != 'active' or item.get('variations') != []:
        return False
    if product.get('catalogProductId') or (product.get('priceCheck') or {}).get('variationId'):
        return False
    try:
        actual, variation = identity(product.get('imageSource') or product.get('productUrl') or '')
        return actual == product['id'] and not variation and product.get('itemId', actual) == actual
    except (ValueError, Unconfirmed):
        return False


def collect(catalog, client, previous=None, now=None, previous_report=None):
    now = now or datetime.now(timezone.utc)
    stamp = now.isoformat(timespec='seconds')
    previous = previous or {}
    result = copy.deepcopy(catalog)
    report = {'generatedAt': stamp, 'source': 'api.mercadolibre.com', 'capabilities': {},
              'pricesConfirmed': 0, 'itemsChecked': 0, 'candidates': [], 'status': 'atenção'}
    probe = Probe(client, report)
    remember_restricted_families(previous_report, report, probe, now)
    signals = {'generatedAt': stamp, 'trendsCheckedAt': previous.get('trendsCheckedAt'),
               'trends': [], 'highlights': [], 'items': {}, 'matches': {}}
    products = {p['id']: p for p in result['products']}
    # Expired item metadata is not presented as current evidence.
    signals['items'] = {k: v for k, v in previous.get('items', {}).items()
                        if k in products and fresh(v.get('checkedAt'), now)}
    ids = [i for i in catalog['publishedIds'] if ID.fullmatch(i) and category(products[i])]
    # Rotate through the published catalog without starving items near its end.
    offset = int(previous.get('cursor', 0)) % max(1, len(ids))
    selected = (ids[offset:] + ids[:offset])[:MAX_ITEMS]
    signals['cursor'] = (offset + len(selected)) % max(1, len(ids))
    for item_id in selected:
        product = products[item_id]
        item = probe.get('items', '/items/' + item_id)
        metadata = item_metadata(product, item, stamp)
        if metadata is None:
            continue
        report['itemsChecked'] += 1
        signals['items'][item_id] = metadata
        if not exact_unvaried(product, item):
            continue
        sale = probe.get('sale_price', f'/items/{item_id}/sale_price?context=channel_marketplace')
        if not isinstance(sale, dict):
            continue
        class PriceResponse:
            def get(self, path):
                return sale
        try:
            updated = observe(product, PriceResponse(), now)
            old = product.get('price')
            if isinstance(old, (int, float)) and old > 0 and abs(updated['price'] / old - 1) > .5:
                metadata['priceReview'] = 'price_jump_requires_review'
                continue
            product.update(updated)
            report['pricesConfirmed'] += 1
        except (ValueError, RuntimeError, TypeError):
            metadata['priceReview'] = 'price_response_unconfirmed'
    # Categories come from verified exact items, not guessed category numbers.
    categories = sorted({v['categoryId'] for v in signals['items'].values() if v.get('categoryId')})[:5]
    cached = fresh(previous.get('trendsCheckedAt'), now, 6)
    if cached:
        signals['trends'] = previous.get('trends', [])
        signals['highlights'] = previous.get('highlights', [])
        report['capabilities']['trends'] = {'status': 'cache', 'checkedAt': previous['trendsCheckedAt']}
    else:
        for cat in [None, *categories]:
            data = probe.get('trends', '/trends/MLB' + ('/' + cat if cat else ''))
            if not isinstance(data, list):
                continue
            signals['trendsCheckedAt'] = stamp
            for pos, entry in enumerate(data[:50]):
                if not isinstance(entry, dict):
                    continue
                keyword = safe_text(entry.get('keyword'), 100)
                if keyword and category({'name': keyword}):
                    group = 'crescimento' if pos < 10 else ('mais_buscadas' if pos < 30 else 'populares')
                    row = {'keyword': keyword, 'categoryId': cat, 'group': group}
                    if row not in signals['trends']:
                        signals['trends'].append(row)
        for cat in categories:
            data = probe.get('highlights', '/highlights/MLB/category/' + cat)
            if not isinstance(data, dict) or not isinstance(data.get('content'), list):
                continue
            for entry in data['content'][:20]:
                valid = ranking_entry(entry, cat, stamp)
                if valid:
                    signals['highlights'].append(valid)
        # Highlights identify product catalogs or listings. Never confuse their IDs.
        for row in signals['highlights']:
            if row['id'] not in products:
                report['candidates'].append(dict(row, affiliateStatus='not_registered', eligibleForPublication=False))
    for item_id in ids:
        matches = matched_trends(products[item_id], signals['trends'])
        if matches:
            signals['matches'][item_id] = matches
    report['trendsFound'] = len(signals['trends'])
    report['catalogTrendMatches'] = len(signals['matches'])
    report['calls'] = getattr(client, 'calls', None)
    caps = list(report['capabilities'].values())
    report['status'] = ('requer intervenção' if probe.auth_failed else
                        'ok' if caps and all(v['status'] in ('ok', 'cache') for v in caps) else
                        'bloqueado' if caps and all(v['status'] == 'bloqueado' for v in caps) else 'atenção')
    return result, signals, report


def load_json(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def write_json(path, value, secrets):
    body = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    if any(secret and secret in body for secret in secrets):
        raise ValueError('Resposta recusada: credencial nos dados')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding='utf-8')


def main(report_only=False):
    current = catalogo.load(ROOT)
    try:
        client = Client()
        updated, signals, report = collect(current, client, load_json(SIGNALS),
            previous_report={} if report_only else load_json(REPORT))
    except AuthError:
        client = None
        updated = current
        signals = {'generatedAt': datetime.now(timezone.utc).isoformat(), 'trends': [], 'items': {}, 'matches': {}}
        report = {'generatedAt': signals['generatedAt'], 'status': 'requer intervenção',
                  'reason': 'ACCESS_TOKEN_missing', 'capabilities': {}, 'pricesConfirmed': 0}
    secrets = [os.getenv(k, '') for k in ('ACCESS_TOKEN', 'CLIENT_SECRET', 'REFRESH_TOKEN', 'GH_SECRETS_TOKEN')]
    secrets.append(client.token if client else '')
    # Check all serialized outputs before any catalog change.
    for value in (updated, signals, report):
        body = json.dumps(value, ensure_ascii=False, allow_nan=False)
        if any(s and s in body for s in secrets):
            raise ValueError('Credencial detectada; dados recusados')
    if updated != current and not report_only:
        files = catalogo.render(updated, ROOT)
        files[catalogo.SOURCE.as_posix()] = catalogo.dumps(updated, pretty=True) + '\n'
        catalogo.write_files(files, ROOT)
    if not report_only:
        write_json(SIGNALS, signals, secrets)
    write_json(REPORT, report, secrets)
    summary = ['## Mercado Livre — API oficial', '',
               'Estado: **' + report['status'] + '**', '',
               'Preços confirmados pela API: ' + str(report['pricesConfirmed']), '',
               '| Recurso | Estado |', '|---|---|']
    summary += ['| ' + name + ' | ' + value['status'] + ' |' for name, value in report['capabilities'].items()]
    summary += ['', 'Resultados de tendências não comprovam desconto, estoque ou comissão.']
    if os.getenv('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as output:
            output.write('\n'.join(summary) + '\n')
    print('API oficial: ' + report['status'] + '; preços confirmados: ' + str(report['pricesConfirmed']))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, RuntimeError, OSError):
        print('API oficial: falha de validação ou conexão; nenhum conteúdo bruto registrado.', file=sys.stderr)
        raise SystemExit(1)
