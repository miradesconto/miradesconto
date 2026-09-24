import copy
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'integracoes' / 'mercadolivre'))
import public_prices


class PublicPricesTest(unittest.TestCase):
    def test_keeps_unconfirmed_items_and_published_identity(self):
        a = {'id': 'MLB1234567890', 'price': 100, 'imageUrl': 'photo',
             'affiliateUrl': 'https://meli.la/test', 'rank': 1}
        b = {'id': 'MLB1234567891', 'price': 200, 'imageUrl': 'photo2',
             'affiliateUrl': 'https://meli.la/test2', 'rank': 2}
        original = {'products': [a, b], 'publishedIds': [a['id'], b['id']],
                    'metadata': {'sourceFile': 'source'}}
        saved = copy.deepcopy(original)

        def refresh(product, timestamp):
            if product['id'] == a['id']:
                return dict(product, price=75, priceCheck={'checkedAt': timestamp}), None
            return None, {'reason': 'exact_product_card_not_found'}

        with patch.object(public_prices, 'refresh_one', side_effect=refresh):
            updated, changed = public_prices.update(original, datetime(2026, 9, 24, tzinfo=timezone.utc), workers=2)
        self.assertEqual(changed, 1)
        self.assertEqual(updated['products'][0]['price'], 75)
        self.assertEqual(updated['products'][1], b)
        self.assertEqual(updated['publishedIds'], saved['publishedIds'])
        self.assertEqual(original, saved)
        self.assertEqual(updated['metadata']['apiSync']['pricesConfirmed'], 1)

    def test_refuses_to_publish_when_all_observations_fail(self):
        original = {'products': [{'id': 'MLB1234567890'}], 'publishedIds': ['MLB1234567890'],
                    'metadata': {}}
        with patch.object(public_prices, 'refresh_one', return_value=(None, {'reason': 'unreachable'})):
            with self.assertRaisesRegex(RuntimeError, 'Nenhum preço confirmado'):
                public_prices.update(original, datetime.now(timezone.utc), workers=1)


if __name__ == '__main__':
    unittest.main()
