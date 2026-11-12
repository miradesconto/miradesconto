import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'integracoes/mercadolivre'))
import mirabot
import api_intelligence as api


class MiraBotTests(unittest.TestCase):
    def test_parse_only_official_short_links_and_dedupe(self):
        result = mirabot.parse_links('https://meli.la/Ab1\n https://meli.la/Ab1 ; https://mercadolivre.com.br/sec/Cd2')
        self.assertEqual(result, ['https://meli.la/Ab1', 'https://mercadolivre.com.br/sec/Cd2'])

    def test_rejects_untracked_or_insecure_links(self):
        for url in ('https://produto.mercadolivre.com.br/MLB-123456789-a',
                    'http://meli.la/abc', 'https://meli.la.evil.com/abc',
                    'https://user@meli.la/abc', 'https://meli.la/abc?x=1'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                mirabot.parse_links(url)
        with self.assertRaises(ValueError):
            mirabot.parse_links(' '.join('https://meli.la/A'+str(n) for n in range(21)))

    def test_preview_does_not_claim_commission_or_publish_new_items(self):
        entries = mirabot.build_preview(
            ['https://meli.la/New', 'https://meli.la/Existing'],
            {'products':[{'id':'MLB1234567890', 'name':'Mouse gamer'}], 'publishedIds':['MLB1234567890']},
            [{'id':'MLB1234567890','affiliateUrl':'https://meli.la/Existing'}])
        self.assertEqual(entries['links'][0]['status'], 'aguardando_validacao')
        self.assertFalse(entries['links'][0]['readyToPublish'])
        self.assertEqual(entries['links'][1]['status'], 'cadastrado')
        self.assertFalse(entries['links'][1]['commissionVerified'])


class ApiRestrictionTests(unittest.TestCase):
    def test_403_is_not_repeated_until_24h_and_trends_still_work(self):
        now = datetime(2026,11,12,12,0,tzinfo=timezone.utc)
        item_id='MLB1234567890'
        catalog={'products':[{'id':item_id,'name':'Notebook gamer',
               'category':'Notebooks'}], 'publishedIds':[item_id]}
        class Client:
            def __init__(self):
                self.paths=[]
            def get(self,path):
                self.paths.append(path)
                if path.startswith('/items/'): raise api.AccessError(403)
                if path.startswith('/trends/'): return [{'keyword':'notebook gamer'}]
                raise AssertionError(path)
        first=Client()
        _,sig,report=api.collect(catalog,first,now=now)
        self.assertEqual(report['capabilities']['items']['http'],403)
        self.assertEqual(sum(p.startswith('/items/') for p in first.paths),1)
        second=Client()
        _,_,next_report=api.collect(catalog,second,now=now+timedelta(minutes=15),
                                    previous_report=report)
        self.assertEqual(sum(p.startswith('/items/') for p in second.paths),0)
        self.assertTrue(next_report['capabilities']['items']['cached'])
        self.assertEqual(report['capabilities']['items']['lastAttemptAt'],
                         next_report['capabilities']['items']['lastAttemptAt'])
        self.assertIn('/trends/MLB',second.paths)
        third=Client()
        api.collect(catalog,third,now=now+timedelta(hours=25),previous_report=next_report)
        self.assertEqual(sum(p.startswith('/items/') for p in third.paths),1)

    def test_sale_price_denial_is_cached_independently(self):
        now=datetime(2026,11,12,12,tzinfo=timezone.utc)
        report={'generatedAt':now.isoformat(), 'capabilities': {
            'sale_price': {'status':'bloqueado','http':403,'lastAttemptAt':now.isoformat()}}}
        new={'generatedAt':(now+timedelta(minutes=15)).isoformat(), 'capabilities': {}}
        class Fake: pass
        probe=api.Probe(Fake(),new)
        api.remember_restricted_families(report,new,probe,now+timedelta(minutes=15))
        self.assertIn('sale_price',probe.stopped)
        self.assertNotIn('items',probe.stopped)
        self.assertEqual(new['capabilities']['sale_price']['http'],403)


if __name__ == '__main__':
    unittest.main()
