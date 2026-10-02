import copy
import sys
import unittest
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'integracoes'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'integracoes/mercadolivre'))
from tech_policy import category, reconcile
import public_prices

class TechPolicyTest(unittest.TestCase):
    def product(self, name, item='MLB1234567890'):
        return dict(id=item, name=name, price=50, oldPrice=100,
                    priceCheck=dict(status='verified', currency='BRL', price=50, oldPrice=100),
                    rank=1, featured=True)

    def test_incidental_keywords_do_not_admit_other_niches(self):
        for name in ('Luva academia grip', 'Laptop infantil Barbie', 'Carregador parafusadeira',
                     'Monitor pressão arterial', 'Campainha sino de mesa', 'Projetor astronauta luminária'):
            self.assertIsNone(category({'name': name}), name)
        self.assertEqual(category({'name': 'Notebook Acer Nitro V15'}), 'Notebooks')
        self.assertEqual(category({'name': 'Mouse gamer sem fio'}), 'Setup')

    def test_discount_ending_removes_publication_but_keeps_registration(self):
        p = self.product('Mouse gamer')
        c = dict(products=[p], publishedIds=[p['id']], metadata={'niche':'tech'})
        p['oldPrice'] = None
        p['priceCheck']['oldPrice'] = None
        reconcile(c)
        self.assertEqual(c['publishedIds'], [])
        self.assertEqual(len(c['products']), 1)

    def test_weekly_scan_excludes_nontech_and_never_rotates_it_back(self):
        mouse = self.product('Mouse gamer')
        kitchen = self.product('Air fryer', 'MLB1234567891')
        c = dict(products=[mouse, kitchen], publishedIds=[mouse['id']], metadata={'niche':'tech'})
        with patch.object(public_prices, 'refresh_one', side_effect=lambda p,t:(copy.deepcopy(p), None)) as refresh:
            result, _ = public_prices.update(c, datetime.now(timezone.utc), workers=1, rotate=True)
        self.assertEqual(refresh.call_count, 1)
        self.assertEqual(result['publishedIds'], [mouse['id']])

    def test_missing_price_evidence_does_not_publish(self):
        p = self.product('Mouse gamer')
        p.pop('priceCheck')
        c = dict(products=[p], publishedIds=[p['id']], metadata={'niche':'tech'})
        reconcile(c)
        self.assertEqual(c['publishedIds'], [])

