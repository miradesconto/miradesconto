import sys
import unittest
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'integracoes' / 'mercadolivre'))
from import_links import affiliate, allowed, prepare, parse_page

class ImportTest(unittest.TestCase):
    def test_affiliate_card_resolution(self):
        body = (Path(__file__).parent / 'fixtures/MLB2766771378.html').read_text()
        body = body.replace('Creatina 1kg Suplemento Monohidratada em pó 100% Pura - Soldiers Nutrition', 'Mouse Logitech G305')
        body = body.replace('<div class="poly-card">', '<div class="poly-card"><img src="https://http2.mlstatic.com/test.jpg">')
        row = parse_page(body, 'https://www.mercadolivre.com.br/social/owner', 'https://meli.la/example')
        self.assertEqual(row['id'], 'MLB2766771378')
        self.assertEqual(row['_observation']['price'], 68.90)
        self.assertEqual(row['affiliateUrl'], 'https://meli.la/example')
        with self.assertRaises(ValueError):
            parse_page(body + body.replace('MLB2766771378', 'MLB2766771379'),
                       'https://www.mercadolivre.com.br/social/owner', 'https://meli.la/example')

    def test_hosts(self):
        for url in ['http://meli.la/abc','https://meli.la.evil.com/abc','https://user@meli.la/abc','https://127.0.0.1/sec/a']:
            self.assertFalse(affiliate(url))
            self.assertFalse(allowed(url))
        self.assertTrue(affiliate('https://mercadolivre.com/sec/ABC123'))
    def test_original_link_and_promotion(self):
        current = {'products':[], 'publishedIds':[], 'metadata':{'niche':'tech'}}
        link = 'https://meli.la/abc'
        def resolver(url):
            return dict(id='MLB123456789',name='Notebook Acer',category='Notebooks',affiliateUrl=url,productUrl='https://produto.mercadolivre.com.br/MLB-123456789-x',imageUrl='https://http2.mlstatic.com/x.jpg')
        def verify(p, now):
            return dict(p, price=100,oldPrice=200,available=None,priceCheck={'status':'verified','price':100,'oldPrice':200,'currency':'BRL'})
        updated, archive = prepare(current, [], [link], datetime.now(timezone.utc), resolver, verify)
        self.assertEqual(updated['publishedIds'], ['MLB123456789'])
        self.assertEqual(archive[0]['affiliateUrl'], link)
        self.assertEqual(current['products'], [])
        with self.assertRaises(ValueError):
            prepare(updated,archive,[link],datetime.now(timezone.utc),resolver,verify)
    def test_no_discount_stays_unpublished(self):
        current = {'products':[], 'publishedIds':[], 'metadata':{'niche':'tech'}}
        def resolver(url):
            return dict(id='MLB123456789',name='Mouse Logitech',affiliateUrl=url,productUrl='x')
        updated, _ = prepare(current,[],['https://meli.la/a'],datetime.now(timezone.utc),resolver,lambda p,n:dict(p,price=100,oldPrice=None))
        self.assertEqual(updated['publishedIds'], [])

if __name__ == '__main__': unittest.main()
