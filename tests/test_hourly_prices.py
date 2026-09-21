import copy
import io
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import HTTPError
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'integracoes/mercadolivre'))
import hourly_prices as h
from qualidade import usable_price
NOW = datetime(2026,9,21,22,tzinfo=timezone.utc)
ID, WIN, CAT = 'MLB1234567890', 'MLB9876543210', 'MLB45070708'

class Prices(unittest.TestCase):
    def setUp(self):
        self.p = dict(id=ID,price=100,oldPrice=120,affiliateUrl='https://meli.la/example')
        self.c = Mock()
        self.c.get.return_value = dict(amount=80,regular_amount=100,currency_id='BRL')

    def test_direct_and_no_churn_and_renewal(self):
        r = h.observe(self.p,self.c,NOW)
        self.assertEqual((r['price'],r['discount'],r['id'],r['affiliateUrl']), (80,20,ID,self.p['affiliateUrl']))
        self.assertTrue(usable_price(r,NOW))
        self.assertEqual(h.observe(r,self.c,NOW+timedelta(hours=1)),r)
        renewed = h.observe(r,self.c,NOW+timedelta(hours=12))
        self.assertNotEqual(renewed['lastUpdated'],r['lastUpdated'])
        self.assertTrue(usable_price(renewed,NOW+timedelta(hours=25)))
        self.assertEqual(self.p['price'],100)

    def test_buy_box(self):
        for extra in [dict(catalogProductId=CAT),dict(productUrl=f'https://www.mercadolivre.com.br/example/p/{CAT}')]:
            self.c.get.side_effect=[dict(id=CAT,buy_box_winner=dict(item_id=WIN)),dict(amount=50,currency_id='BRL')]
            r=h.observe(dict(self.p,**extra),self.c,NOW)
            self.assertEqual((r['itemId'],r['id'],r['affiliateUrl']),(WIN,ID,self.p['affiliateUrl']))
            self.assertIsNone(r['oldPrice'])
            self.assertIsNone(r['discount'])
            self.assertTrue(usable_price(r,NOW))
            r['itemId']=ID
            self.assertFalse(usable_price(r,NOW))

    def test_invalid_and_missing_winner(self):
        for value in [0,-1,True,'50',float('nan'),float('inf'),.001]:
            self.c.get.return_value=dict(amount=value,currency_id='BRL')
            with self.assertRaises(ValueError): h.observe(self.p,self.c,NOW)
        self.c.get.return_value=dict(amount=20,currency_id='USD')
        with self.assertRaises(ValueError): h.observe(self.p,self.c,NOW)
        for data in [dict(id=CAT),dict(id='wrong',buy_box_winner=dict(item_id=WIN))]:
            self.c.get.return_value=data
            with self.assertRaises(ValueError): h.observe(dict(self.p,catalogProductId=CAT),self.c,NOW)

    def test_explicit_item_up_url(self):
        h.observe(dict(self.p,itemId=WIN,productUrl='https://www.mercadolivre.com.br/up/MLBU1234567890'),self.c,NOW)
        self.c.get.assert_called_once_with(f'/items/{WIN}/sale_price?context=channel_marketplace')

    @patch.object(h.time,'sleep')
    def test_partial_and_global_failure(self,sleep):
        original=dict(products=[self.p,dict(self.p,id=WIN)],publishedIds=[ID])
        before=copy.deepcopy(original)
        self.c.get.side_effect=[h.ApiError(404),dict(amount=80,currency_id='BRL')]
        result,changed=h.update(original,self.c,NOW)
        self.assertEqual(changed,1)
        self.assertEqual(result['products'][0],self.p)
        self.assertEqual(original,before)
        self.assertEqual(result['publishedIds'],[ID])
        self.c.get.side_effect=h.ApiError(403)
        with self.assertRaisesRegex(RuntimeError,'Cinco falhas'): h.update(dict(products=[self.p]*6),self.c,NOW)

    def test_real_catalog_render(self):
        original=h.catalogo.load(ROOT)
        result=copy.deepcopy(original)
        i=next(i for i,p in enumerate(result['products']) if p['id']==result['publishedIds'][0])
        p=result['products'][i]
        p['catalogProductId']=CAT
        self.c.get.side_effect=[dict(id=CAT,buy_box_winner=dict(item_id=WIN)),dict(amount=50,regular_amount=100,currency_id='BRL')]
        result['products'][i]=h.observe(p,self.c,NOW)
        files=h.catalogo.render(result,ROOT)
        self.assertEqual(result['publishedIds'],original['publishedIds'])
        self.assertEqual([p['affiliateUrl'] for p in result['products']],[p['affiliateUrl'] for p in original['products']])
        self.assertIn('"itemId":"MLB9876543210"',files['catalogo/produtos-001.json'])

class Auth(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,{**{k:'test-only' for k in h.REQUIRED},'GITHUB_REPOSITORY':'test/repo'},clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_missing(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaisesRegex(h.AuthError,'CLIENT_ID, CLIENT_SECRET, ACCESS_TOKEN, REFRESH_TOKEN, GH_SECRETS_TOKEN'): h.Client()

    @patch.object(h,'gh')
    @patch.object(h,'request')
    def test_refresh_order(self,request,gh):
        request.side_effect=[h.ApiError(401),dict(access_token='new-access',refresh_token='new-refresh'),dict(amount=1)]
        self.assertEqual(h.Client().get('/test'),dict(amount=1))
        self.assertEqual(gh.call_args_list[1].args,(['secret','set','REFRESH_TOKEN','--repo','test/repo'],'new-refresh'))
        self.assertEqual(gh.call_args_list[2].args,(['secret','set','ACCESS_TOKEN','--repo','test/repo'],'new-access'))
        self.assertEqual(request.call_args.args,('/test','new-access'))

    @patch.object(h,'gh',side_effect=h.AuthError('No permission'))
    @patch.object(h,'request')
    def test_no_refresh_on_permission_failure(self,request,gh):
        with self.assertRaises(h.AuthError): h.Client().refresh()
        request.assert_not_called()

    @patch.object(h.time,'sleep')
    @patch.object(h,'urlopen')
    def test_retry_and_redaction(self,urlopen,sleep):
        response=Mock()
        response.__enter__=Mock(return_value=io.StringIO('{"amount":42}'))
        response.__exit__=Mock(return_value=False)
        urlopen.side_effect=[HTTPError(h.API,429,'limited',{'Retry-After':'7'},io.BytesIO(b'secret')),response]
        self.assertEqual(h.request('/test'),dict(amount=42))
        sleep.assert_called_once_with(7)
        urlopen.side_effect=HTTPError(h.API,403,'forbidden',{},io.BytesIO(b'secret'))
        with self.assertRaises(h.ApiError) as caught: h.request('/test','secret')
        self.assertNotIn('secret',str(caught.exception))

    @patch.object(h.time,'sleep')
    @patch.object(h,'urlopen',side_effect=TimeoutError)
    def test_post_not_retried(self,urlopen,sleep):
        with self.assertRaises(RuntimeError): h.request('/oauth/token',form={'refresh_token':'secret'})
        self.assertEqual(urlopen.call_count,1)
        sleep.assert_not_called()
