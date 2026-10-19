import importlib.util
from pathlib import Path
from datetime import datetime, timedelta, timezone
import unittest

spec = importlib.util.spec_from_file_location('freshness', Path(__file__).resolve().parents[1] / 'integracoes/automacao/price_freshness.py')
freshness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(freshness)

class FreshnessTests(unittest.TestCase):
    def catalog(self, age=0, count=10, link='https://meli.la/Individual'):
        now = datetime(2026, 10, 19, 15, tzinfo=timezone.utc)
        rows = [{'id': str(i), 'price': 10, 'oldPrice': 20, 'affiliateUrl': link,
                 'priceCheck': {'status': 'verified', 'method': 'poly-card-v1',
                    'itemId': str(i), 'currency': 'BRL', 'price': 10, 'oldPrice': 20,
                    'checkedAt': (now-timedelta(minutes=age)).isoformat()}}
                for i in range(count)]
        return {'products': rows, 'publishedIds': [p['id'] for p in rows]}, now

    def test_recent_full_selection_does_not_recollect(self):
        catalog, now = self.catalog()
        self.assertFalse(freshness.assess(catalog, now)['needsRefresh'])

    def test_recover_before_prices_expire(self):
        catalog, now = self.catalog(age=61)
        result = freshness.assess(catalog, now)
        self.assertEqual(result['freshOffers'], 10)
        self.assertTrue(result['needsRefresh'])

    def test_expired_or_generic_offers_do_not_satisfy_coverage(self):
        for kwargs in ({'age': 121}, {'link': 'https://meli.la/1pyBZm8'}, {'count': 9}):
            catalog, now = self.catalog(**kwargs)
            self.assertTrue(freshness.assess(catalog, now)['needsRefresh'])

    def test_unpublished_offers_do_not_satisfy_coverage(self):
        catalog, now = self.catalog()
        catalog['publishedIds'] = []
        self.assertEqual(freshness.assess(catalog, now)['freshOffers'], 0)
