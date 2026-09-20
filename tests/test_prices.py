import copy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'integracoes'))
sys.path.insert(0, str(ROOT / 'integracoes/mercadolivre'))
from product_card import extract, identity, Unconfirmed
from qualidade import usable_price
import rebuild_catalog

NOW = datetime(2026, 9, 20, 20, 0, tzinfo=timezone.utc)
ID = 'MLB4592320910'
URL = 'https://produto.mercadolivre.com.br/MLB-4592320910-camisetas-_JM?searchVariation=186408020315'
FIXTURE = ROOT / 'tests/fixtures/MLB4592320910.html'


class PriceTests(unittest.TestCase):
    def setUp(self):
        self.body = FIXTURE.read_text(encoding='utf-8')
        self.product = {'id':ID, 'name':'Camisetas', 'price':59.99, 'oldPrice':135.41,
                        'productUrl':URL, 'affiliateUrl':'https://meli.la/1TJh5DW',
                        'imageUrl':'https://http2.mlstatic.com/image.webp', 'available':True}

    def refreshed(self, body=None, product=None):
        with patch.object(rebuild_catalog, 'fetch_affiliate_page', return_value=('https://www.mercadolivre.com.br/social/example',body or self.body)):
            return rebuild_catalog.refresh_one(product or self.product, NOW.isoformat())

    def test_real_card_price_and_variation(self):
        observed = extract(self.body, ID, URL)
        self.assertEqual(observed, {'price':49.99,'oldPrice':135.41,'variationId':'186408020315','currency':'BRL'})

    def test_other_real_card_shapes(self):
        for pid, price in [('MLB3616720913',49.99), ('MLB2766771378',68.9)]:
            with self.subTest(pid=pid):
                body=(ROOT/'tests/fixtures'/f'{pid}.html').read_text(encoding='utf-8')
                reference=f'https://www.mercadolivre.com.br/example/p/MLB18725310#wid={pid}'
                self.assertEqual(extract(body,pid,reference)['price'],price)

    def test_neighbor_price_and_tracking_id_do_not_match(self):
        body=self.body.replace('MLB-4592320910','MLB-9999999999').replace('?searchVariation=',f'?tracking_id={ID}&searchVariation=')
        with self.assertRaisesRegex(Unconfirmed,'exact_product_card_not_found'):
            extract(body+f'<script>{{"id":"{ID}","current_price":0.01}}</script>',ID,URL)

    def test_prefix_id_does_not_match(self):
        with self.assertRaises(Unconfirmed): extract(self.body.replace(ID[3:],ID[3:]+'9'),ID,URL)

    def test_different_or_missing_variation_is_rejected(self):
        for body in [self.body.replace('186408020315','186408020316'),self.body.replace('searchVariation=186408020315','')]:
            with self.assertRaisesRegex(Unconfirmed,'variation_mismatch'): extract(body,ID,URL)

    def test_catalog_id_is_not_item_id(self):
        self.assertEqual(identity('https://www.mercadolivre.com.br/x/p/MLB18725310#wid=MLB2766771378'),('MLB2766771378',None))
        with self.assertRaises(Unconfirmed): identity('https://www.mercadolivre.com.br/x/p/MLB18725310')

    def test_conflicting_identity_or_domain_is_rejected(self):
        for url in [URL+'&item_id=MLB9999999999',URL.replace('produto.mercadolivre.com.br','mercadolivre.com.br.example.org')]:
            with self.assertRaises(Unconfirmed): identity(url)

    def test_duplicate_matching_cards_must_agree(self):
        self.assertEqual(extract(self.body+self.body,ID,URL)['price'],49.99)
        conflicting=self.body.replace('>49<','>48<')
        with self.assertRaisesRegex(Unconfirmed,'conflicting_product_cards'):
            extract(self.body+conflicting,ID,URL)

    def test_truncated_or_missing_card_is_rejected(self):
        for body in [self.body[:len(self.body)//2],'<html>Falha de acesso</html>',self.body.replace('poly-card','unknown-card')]:
            with self.assertRaises(Unconfirmed): extract(body,ID,URL)

    def test_conditional_price_currency_and_cents(self):
        for body in [self.body.replace('poly-component__price">','poly-component__price">Com cupom '),self.body.replace('R$','US$'),self.body.replace('>99<','>999<')]:
            with self.assertRaises(Unconfirmed): extract(body,ID,URL)

    def test_refresh_preserves_links_and_does_not_invent_stock(self):
        result,error=self.refreshed()
        self.assertIsNone(error)
        self.assertIsNone(result['available'])
        self.assertEqual(result['availabilityStatus'],'unknown')
        for key in ['id','affiliateUrl','imageUrl','productUrl']:
            self.assertEqual(result[key],self.product[key])
        self.assertTrue(usable_price(result,NOW))

    def test_large_price_change_requires_review(self):
        p=copy.deepcopy(self.product);p['price']=150
        result,error=self.refreshed(product=p)
        self.assertIsNone(result)
        self.assertEqual(error['reason'],'price_jump_requires_review')

    def test_unreachable_page_is_not_a_stock_status(self):
        with patch.object(rebuild_catalog,'fetch_affiliate_page',return_value=None):
            result,error=rebuild_catalog.refresh_one(self.product,NOW.isoformat())
        self.assertIsNone(result)
        self.assertEqual(error['reason'],'affiliate_page_unreachable')
        self.assertTrue(self.product['available'])

    def test_unknown_availability_is_ineligible_for_social_posts(self):
        sys.path.insert(0, str(ROOT / 'integracoes/social'))
        from gerar_pauta import eligible
        result,_=self.refreshed()
        with patch('gerar_pauta.usable_price', return_value=True):
            self.assertFalse(eligible(result))
        result['available']=True
        result['availabilityStatus']='available'
        with patch('gerar_pauta.usable_price', return_value=False):
            self.assertFalse(eligible(result))

    def test_old_future_unverified_and_altered_prices_are_unusable(self):
        p,_=self.refreshed()
        self.assertTrue(usable_price(p,NOW+timedelta(hours=24)))
        self.assertFalse(usable_price(p,NOW+timedelta(hours=24,seconds=1)))
        self.assertFalse(usable_price(p,NOW-timedelta(seconds=1)))
        self.assertFalse(usable_price(self.product,NOW))
        for field,value in [('price',99.9),('oldPrice',999),('available',False)]:
            changed=copy.deepcopy(p);changed[field]=value
            self.assertFalse(usable_price(changed,NOW))
        for stamp in ['2026-09-20T20:00:00','invalid',None]:
            changed=copy.deepcopy(p);changed['priceCheck']['checkedAt']=stamp
            self.assertFalse(usable_price(changed,NOW))


if __name__ == '__main__': unittest.main()
