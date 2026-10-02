import sys
import unittest
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'integracoes' / 'mercadolivre'))
from import_links import affiliate, allowed, prepare

class ImportTest(unittest.TestCase):
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
