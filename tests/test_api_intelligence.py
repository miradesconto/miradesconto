import copy
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'integracoes/mercadolivre'))
import api_intelligence as api

NOW = datetime(2026, 11, 9, 15, tzinfo=timezone.utc)
ID = 'MLB1234567890'
PRODUCT = {'id': ID, 'name': 'Notebook Lenovo Ryzen 5', 'category': 'Notebooks',
           'productUrl': 'https://produto.mercadolivre.com.br/MLB-1234567890-notebook-_JM',
           'affiliateUrl': 'https://meli.la/Test', 'price': 1000}
CATALOG = {'products': [PRODUCT], 'publishedIds': [ID]}
ITEM = {'id': ID, 'site_id': 'MLB', 'currency_id': 'BRL', 'status': 'active',
        'permalink': PRODUCT['productUrl'], 'variations': [], 'category_id': 'MLB1648',
        'attributes': [{'id': 'BRAND', 'value_name': 'Lenovo'}]}

class Client:
    def __init__(self, blocked=(), item=None):
        self.paths = []
        self.blocked = blocked
        self.item = ITEM if item is None else item
    def get(self, path):
        self.paths.append(path)
        if any(word in path for word in self.blocked):
            raise api.AccessError(403)
        if path == '/items/' + ID:
            return copy.deepcopy(self.item)
        if '/sale_price?' in path:
            return {'amount': 900, 'regular_amount': 1000, 'currency_id': 'BRL'}
        if path.startswith('/trends/'):
            return [{'keyword': 'Notebook Lenovo'}, {'keyword': 'roupa infantil'}]
        if path.startswith('/highlights/'):
            return {'content': [{'id': 'MLB2345678901', 'type': 'PRODUCT', 'position': 1}]}
        raise AssertionError(path)

class IntelligenceTests(unittest.TestCase):
    def test_real_data_reaches_catalog_and_signals_preserving_affiliate(self):
        before = copy.deepcopy(CATALOG)
        result, signals, report = api.collect(CATALOG, Client(), now=NOW)
        self.assertEqual(CATALOG, before)
        product = result['products'][0]
        self.assertEqual(product['price'], 900)
        self.assertEqual(product['affiliateUrl'], PRODUCT['affiliateUrl'])
        self.assertEqual(product['priceCheck']['itemId'], ID)
        self.assertIsNone(product['available'])
        self.assertEqual(signals['matches'][ID], ['Notebook Lenovo'])
        self.assertFalse(signals['items'][ID]['stockConfirmed'])
        self.assertEqual(report['pricesConfirmed'], 1)
        self.assertEqual(report['status'], 'ok')
        self.assertFalse(report['candidates'][0]['eligibleForPublication'])
        self.assertNotIn('affiliateUrl', report['candidates'][0])

    def test_official_highlights_accept_mlb_and_mlbu_formats(self):
        stamp = NOW.isoformat()
        self.assertEqual(api.ranking_entry(
            {'id': 'MLBU3013800008', 'type': 'USER_PRODUCT'},
            'MLB432825', stamp
        ), {'id': 'MLBU3013800008', 'type': 'USER_PRODUCT', 'position': None,
            'categoryId': 'MLB432825', 'checkedAt': stamp})
        self.assertEqual(api.ranking_entry(
            {'id': 'MLB2345678901', 'type': 'PRODUCT', 'position': 2},
            'MLB432825', stamp
        )['position'], 2)
        self.assertIsNone(api.ranking_entry(
            {'id': 'MLBU3013800008', 'type': 'ITEM', 'position': 1},
            'MLB432825', stamp))
        self.assertIsNone(api.ranking_entry(
            {'id': 'MLB2345678901', 'type': 'PRODUCT', 'position': 21},
            'MLB432825', stamp))

    def test_denied_items_do_not_disable_trends(self):
        result, signals, report = api.collect(CATALOG, Client(blocked=['/items/']), now=NOW)
        self.assertEqual(result, CATALOG)
        self.assertEqual(report['capabilities']['items']['status'], 'bloqueado')
        self.assertEqual(signals['matches'][ID], ['Notebook Lenovo'])
        self.assertEqual(report['pricesConfirmed'], 0)

    def test_price_denied_preserves_previous_verified_price(self):
        result, signals, report = api.collect(CATALOG, Client(blocked=['sale_price']), now=NOW)
        self.assertEqual(result, CATALOG)
        self.assertEqual(report['capabilities']['sale_price']['http'], 403)
        self.assertIn(ID, signals['items'])

    def test_wrong_identity_variation_or_catalog_never_changes_price(self):
        for change in ({'id': 'MLB9999999999'}, {'currency_id': 'USD'}, {'site_id': 'MLA'},
                       {'variations': [{'id': 12}]}, {'variations': None}, {'status': 'paused'}):
            with self.subTest(change=change):
                client = Client(item=dict(ITEM, **change))
                result, _, report = api.collect(CATALOG, client, now=NOW)
                self.assertEqual(result, CATALOG)
                self.assertEqual(report['pricesConfirmed'], 0)
                self.assertFalse(any('sale_price' in p for p in client.paths))
        for change in ({'catalogProductId': 'MLB2345678901'}, {'priceCheck': {'variationId': '99'}},
                       {'productUrl': PRODUCT['productUrl'] + '?searchVariation=1'}):
            catalog = copy.deepcopy(CATALOG)
            catalog['products'][0].update(change)
            result, _, _ = api.collect(catalog, Client(), now=NOW)
            self.assertEqual(result, catalog)

    def test_cache_expires_and_failed_refresh_never_promotes_old_trends(self):
        _, signals, _ = api.collect(CATALOG, Client(), now=NOW)
        client = Client()
        _, cached, _ = api.collect(CATALOG, client, signals, now=NOW+timedelta(hours=1))
        self.assertFalse(any('/trends/' in p for p in client.paths))
        self.assertEqual(cached['trendsCheckedAt'], signals['trendsCheckedAt'])
        _, expired, _ = api.collect(CATALOG, Client(blocked=['/trends/']), signals, now=NOW+timedelta(days=2))
        self.assertEqual(expired['matches'], {})
        self.assertEqual(expired['trends'], [])

    def test_403_stops_family_but_not_other_capabilities(self):
        report = {'capabilities': {}}
        client = Client(blocked=['/items/'])
        probe = api.Probe(client, report)
        probe.get('items', '/items/' + ID)
        probe.get('items', '/items/MLB2345678901')
        self.assertEqual(len(client.paths), 1)
        self.assertIsInstance(probe.get('trends', '/trends/MLB'), list)

    def test_token_echo_never_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'result.json'
            with self.assertRaises(ValueError):
                api.write_json(path, {'keyword': 'synthetic-secret'}, ['synthetic-secret'])
            self.assertFalse(path.exists())

    def test_partial_word_does_not_match_model(self):
        self.assertEqual(api.matched_trends({'name': 'iPhone 150'}, [{'keyword': 'iPhone 15'}]), [])

    def test_transient_and_auth_failures_are_distinct(self):
        for exc, status in [(api.AccessError(429), 'atenção'), (api.AuthError('test'), 'requer intervenção')]:
            with patch.object(Client, 'get', side_effect=exc):
                result, _, report = api.collect(CATALOG, Client(), now=NOW)
            self.assertEqual(result, CATALOG)
            self.assertEqual(report['capabilities']['items']['status'], status)

    def test_renewal_once_and_retry_read_after_401(self):
        with patch.dict(api.os.environ, {'ACCESS_TOKEN': 'old-test', 'CLIENT_ID': 'id',
             'CLIENT_SECRET': 'secret-test', 'REFRESH_TOKEN': 'refresh-test', 'GH_SECRETS_TOKEN': 'gh-test'}):
            client = api.Client()
            def refresh():
                client.refreshed = True
                client.token = 'new-test'
            with patch.object(api.Transport, 'get', side_effect=[api.AccessError(401), []]), \
                 patch.object(client, 'refresh', side_effect=refresh) as renewal:
                self.assertEqual(client.get('/trends/MLB'), [])
                renewal.assert_called_once()

if __name__ == '__main__':
    unittest.main()

class ConsumptionTests(unittest.TestCase):
    def test_fresh_api_price_not_overwritten_by_public_page(self):
        import public_prices
        result, _, _ = api.collect(CATALOG, Client(), now=NOW)
        result['metadata'] = {}
        with patch.object(public_prices, 'refresh_one') as fetch, \
             patch.object(public_prices, 'reconcile'), \
             patch('tech_policy.eligible', return_value=True):
            refreshed, _ = public_prices.update(result, NOW)
        fetch.assert_not_called()
        self.assertEqual(refreshed['products'][0]['price'], 900)

    def test_social_ignores_expired_and_future_trends(self):
        from integracoes.social import gerar_pauta as social
        for delta, expected in [(0, ['Notebook Lenovo']), (-25, []), (1, [])]:
            signals = {'trendsCheckedAt': (NOW+timedelta(hours=delta)).isoformat(),
                       'matches': {ID: ['Notebook Lenovo']}}
            self.assertEqual(social.api_trend_matches(PRODUCT, signals, NOW), expected)
