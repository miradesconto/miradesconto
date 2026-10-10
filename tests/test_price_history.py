import copy
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'integracoes/mercadolivre'))
from price_history import observation, archive, HistoryClient, normalized_row
from unittest.mock import Mock
import requests

class MemoryClient:
    def __init__(self):
        self.data={};self.calls=[];self.pending=False;self.corrupt=False
    def post(self,key,rows,mode='normal'):
        self.calls.append((key,rows,mode))
        stored=self.data.setdefault(key,{})
        for row in rows: stored[(row['at'],row['itemId'],row['variationId'])]=row
        return {'saved':True,'productId':key,'kvPublished':mode!='stage' and not self.pending,'reason':'daily_budget' if self.pending else 'published'}
    def read(self,key,verify=False):
        assert verify
        return {'productId':key,'currency':'BRL','observations':[] if self.corrupt else list(self.data[key].values())}

class HistoryTest(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026,10,6,tzinfo=timezone.utc)
        self.p = {'id':'MLB1234567890','price':70,'oldPrice':100,'priceCheck':{'status':'verified','method':'poly-card-v1','currency':'BRL','itemId':'MLB1234567890','variationId':'123','price':70,'oldPrice':100,'checkedAt':self.now.isoformat()}}
    def test_rejects_mismatched_and_invalid_evidence(self):
        for key,value in [('itemId','MLB9999999999'),('price',71),('method','unknown'),('checkedAt','2026-10-06'),('checkedAt',(self.now+timedelta(hours=1)).isoformat()),('checkedAt',(self.now-timedelta(days=181)).isoformat())]:
            p=copy.deepcopy(self.p);p['priceCheck'][key]=value
            self.assertIsNone(observation(p,self.now))
    def test_deduplication_and_variation_separation(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'dados').mkdir()
            client=MemoryClient()
            def save(p):
                (root/'dados/catalogo.json').write_text(json.dumps({'products':[p],'publishedIds':[p['id']]}));archive(root=root,now=self.now,client=client)
            save(self.p);save(self.p)
            self.assertEqual(len(client.data[self.p['id']]),1)
            other=copy.deepcopy(self.p);other['priceCheck']['variationId']='456';save(other)
            self.assertEqual(len(client.data[self.p['id']]),2)
            self.assertFalse((root/'historico').exists())

    def migration_fixture(self, root):
        (root/'dados').mkdir();(root/'historico').mkdir()
        (root/'dados/catalogo.json').write_text(json.dumps({'products':[self.p],'publishedIds':[self.p['id']]}))
        path=root/'historico'/f"{self.p['id']}.json"
        path.write_text(json.dumps({'productId':self.p['id'],'currency':'BRL','observations':[observation(self.p,self.now)]}))
        return path

    def test_migration_stages_then_publishes_without_removing_source(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);path=self.migration_fixture(root);before=path.read_bytes();client=MemoryClient()
            archive(root=root,now=self.now,client=client,migrate_local=True)
            self.assertEqual([c[2] for c in client.calls],['stage','migration'])
            self.assertEqual(path.read_bytes(),before)

    def test_cleanup_requires_verified_KV_before_removing_any_file(self):
        for pending,corrupt in [(True,False),(False,True)]:
            with tempfile.TemporaryDirectory() as temp:
                root=Path(temp);path=self.migration_fixture(root);client=MemoryClient();client.pending=pending;client.corrupt=corrupt
                with self.assertRaises(RuntimeError): archive(root=root,now=self.now,client=client,migrate_local=True,cleanup_local=True)
                self.assertTrue(path.exists())

    def test_cleanup_removes_only_after_matching_remote_records(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);path=self.migration_fixture(root)
            archive(root=root,now=self.now,client=MemoryClient(),migrate_local=True,cleanup_local=True)
            self.assertFalse(path.exists())

    def test_second_file_failure_preserves_both_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);first=self.migration_fixture(root);client=MemoryClient()
            other='MLB9999999999';second=root/'historico'/f'{other}.json'
            second.write_text(json.dumps({'productId':other,'currency':'BRL',
                'observations':[{**observation(self.p,self.now),'itemId':other}]}))
            read=client.read
            client.read=lambda key,verify=False: {'productId':other,'currency':'BRL','observations':[]} if key==other else read(key,verify)
            with self.assertRaises(RuntimeError):archive(root=root,now=self.now,client=client,migrate_local=True,cleanup_local=True)
            self.assertTrue(first.exists());self.assertTrue(second.exists())

    def test_dry_run_does_not_require_secret_or_change_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);path=self.migration_fixture(root);before=path.read_bytes()
            result=archive(root=root,now=self.now,migrate_local=True,dry_run=True)
            self.assertEqual(result['observations'],1);self.assertEqual(path.read_bytes(),before)

    def test_invalid_local_document_blocks_migration_before_first_POST(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);path=self.migration_fixture(root)
            data=json.loads(path.read_text());data['currency']='USD';path.write_text(json.dumps(data));client=MemoryClient()
            with self.assertRaises(ValueError):archive(root=root,now=self.now,client=client,migrate_local=True)
            self.assertEqual(client.calls,[]);self.assertTrue(path.exists())

    def test_post_uses_private_auth_and_never_follows_redirect(self):
        session=Mock();session.post.return_value.status_code=200
        session.post.return_value.json.return_value={'saved':True,'productId':self.p['id'],'kvPublished':True}
        token='test-only-long-token-not-a-real-secret-12345'
        client=HistoryClient('https://worker.example',token,session=session)
        client.post(self.p['id'],[observation(self.p,self.now)])
        kwargs=session.post.call_args.kwargs
        self.assertFalse(kwargs['allow_redirects']);self.assertEqual(kwargs['headers']['Authorization'],'Bearer '+token)
        session.post.return_value.status_code=302
        with self.assertRaisesRegex(RuntimeError,'HTTP 302'):client.post(self.p['id'],[])

    def test_network_error_redacts_token_and_retries_idempotent_upload(self):
        token='test-only-long-token-not-a-real-secret-12345';session=Mock()
        session.post.side_effect=requests.RequestException('Authorization: Bearer '+token)
        client=HistoryClient('https://worker.example',token,session=session,sleep=lambda _:None)
        with self.assertRaises(RuntimeError) as caught:client.post(self.p['id'],[])
        self.assertNotIn(token,str(caught.exception));self.assertEqual(session.post.call_count,3)

    def test_expired_row_is_pruned_and_invalid_variation_is_rejected(self):
        row=observation(self.p,self.now);row['at']=(self.now-timedelta(days=181)).isoformat()
        self.assertIsNone(normalized_row(row,self.now))
        row=observation(self.p,self.now);row['variationId']='blue'
        with self.assertRaises(ValueError):normalized_row(row,self.now)
