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

    def test_phone_camera_spec_does_not_make_it_smart_home(self):
        for name in ('Celular Samsung Galaxy S25 Fe 5g, 128gb, Câmera Tripla',
                     'Smartphone Motorola Edge 60 Fusion 5g - Câmera 50mp'):
            self.assertEqual(category({'name': name}), 'Celulares', name)
        self.assertEqual(category({'name': 'Câmera Inteligente Full HD Intelbras'}), 'Smart Home')
        self.assertEqual(category({'name': 'Suporte celular para carro'}), 'Celulares')

    def test_discount_ending_removes_publication_but_keeps_registration(self):
        p = self.product('Mouse gamer')
        c = dict(products=[p], publishedIds=[p['id']], metadata={'niche':'tech'})
        p['oldPrice'] = None
        p['priceCheck']['oldPrice'] = None
        reconcile(c)
        self.assertEqual(c['publishedIds'], [])
        self.assertEqual(len(c['products']), 1)

    def test_confirmed_individual_affiliate_without_discount_is_listed(self):
        from tech_policy import eligible
        p = self.product('Caixa de Som Bluetooth Kapbom', 'MLB7477193852')
        p.update(oldPrice=None, registrationSource='affiliate-panel',
                 affiliateUrl='https://meli.la/2QmhPHR', itemId=p['id'])
        p['priceCheck'].update(method='poly-card-v1', itemId=p['id'], oldPrice=None)
        self.assertTrue(eligible(p))
        catalog = dict(products=[p],publishedIds=[p['id']],metadata={'niche':'tech'})
        reconcile(catalog)
        self.assertEqual(catalog['publishedIds'], [p['id']])
        self.assertFalse(eligible({**p,'priceCheck':{**p['priceCheck'],'price':1}}))
        self.assertFalse(eligible({**p,'registrationSource':'generic'}))
        self.assertFalse(eligible({**p,'affiliateUrl':'https://mercadolivre.com.br/anuncio'}))

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


class FailureReportTest(unittest.TestCase):
    def test_lists_unconfirmed_ids_by_reason_without_prices(self):
        import io, os, tempfile
        from contextlib import redirect_stdout
        with tempfile.TemporaryDirectory() as tmp:
            summary = os.path.join(tmp, 'summary.md')
            with patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': summary}), redirect_stdout(io.StringIO()):
                public_prices.report_failures(
                    {'exact_product_card_not_found': ['MLB2', 'MLB1'], 'price_jump_requires_review': ['MLB3']},
                    {'MLB1', 'MLB3'})
            text = open(summary, encoding='utf-8').read()
        self.assertIn('| `exact_product_card_not_found` | 2 | 1 | MLB1, MLB2 |', text)
        self.assertIn('| `price_jump_requires_review` | 1 | 1 | MLB3 |', text)
        self.assertNotIn('R$', text)

    def test_no_failures_writes_nothing(self):
        import io
        from contextlib import redirect_stdout
        out = io.StringIO()
        with redirect_stdout(out):
            public_prices.report_failures({}, set())
        self.assertEqual(out.getvalue(), '')
