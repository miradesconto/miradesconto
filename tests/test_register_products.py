import copy
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'integracoes' / 'mercadolivre'))
import register_products


class RegisterProductsTest(unittest.TestCase):
    def setUp(self):
        self.existing = {'id': 'MLB1111111111', 'name': 'Existente', 'category': 'Casa',
                         'affiliateUrl': 'https://meli.la/existing'}
        self.catalog = {'products': [self.existing], 'publishedIds': [self.existing['id']]}
        self.archive = [{'id': self.existing['id'], 'affiliateUrl': self.existing['affiliateUrl']}]
        self.entry = {'id': 'MLB1234567890', 'name': 'Produto novo', 'category': 'Casa',
                      'productUrl': 'https://produto.mercadolivre.com.br/MLB-1234567890-produto-_JM',
                      'imageUrl': 'https://http2.mlstatic.com/item.webp',
                      'affiliateUrl': 'https://meli.la/novo123'}
        self.now = datetime(2026, 9, 24, tzinfo=timezone.utc)

    def verify(self, candidate, stamp):
        return dict(candidate, price=42, oldPrice=84, discount=50,
                    priceCheck={'status': 'verified', 'checkedAt': stamp}), None

    def test_registers_verified_item_without_changing_existing_links(self):
        original = copy.deepcopy(self.catalog)
        updated, archive = register_products.prepare(self.catalog, self.archive, [self.entry], self.now, self.verify)
        self.assertEqual(self.catalog, original)
        self.assertEqual(updated['publishedIds'], original['publishedIds'])
        self.assertEqual(updated['products'][-1]['price'], 42)
        self.assertEqual(archive[-1]['affiliateUrl'], self.entry['affiliateUrl'])
        self.assertEqual(archive[0], self.archive[0])

    def test_rejects_mismatch_duplicate_and_unconfirmed_price(self):
        wrong = dict(self.entry, productUrl='https://produto.mercadolivre.com.br/MLB-9999999999-outro-_JM')
        with self.assertRaisesRegex(ValueError, 'outro anúncio'):
            register_products.prepare(self.catalog, self.archive, [wrong], self.now, self.verify)
        duplicate = dict(self.entry, affiliateUrl=self.existing['affiliateUrl'])
        with self.assertRaisesRegex(ValueError, 'repetido'):
            register_products.prepare(self.catalog, self.archive, [duplicate], self.now, self.verify)
        with self.assertRaisesRegex(ValueError, 'Preço não confirmado'):
            register_products.prepare(self.catalog, self.archive, [self.entry], self.now,
                                      lambda *_: (None, {'reason': 'exact_product_card_not_found'}))


if __name__ == '__main__':
    unittest.main()
