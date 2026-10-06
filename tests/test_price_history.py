import copy
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'integracoes/mercadolivre'))
from price_history import observation, archive

class HistoryTest(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026,10,6,tzinfo=timezone.utc)
        self.p = {'id':'MLB1234567890','price':70,'oldPrice':100,'priceCheck':{'status':'verified','method':'poly-card-v1','currency':'BRL','itemId':'MLB1234567890','variationId':'blue','price':70,'oldPrice':100,'checkedAt':self.now.isoformat()}}
    def test_rejects_mismatched_and_invalid_evidence(self):
        for key,value in [('itemId','MLB9999999999'),('price',71),('method','unknown'),('checkedAt','2026-10-06'),('checkedAt',(self.now+timedelta(hours=1)).isoformat()),('checkedAt',(self.now-timedelta(days=181)).isoformat())]:
            p=copy.deepcopy(self.p);p['priceCheck'][key]=value
            self.assertIsNone(observation(p,self.now))
    def test_deduplication_and_variation_separation(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'dados').mkdir()
            def save(p):
                (root/'dados/catalogo.json').write_text(json.dumps({'products':[p]}));archive(root=root,now=self.now)
            save(self.p);save(self.p)
            path=root/'historico/MLB1234567890.json'
            self.assertEqual(len(json.loads(path.read_text())['observations']),1)
            other=copy.deepcopy(self.p);other['priceCheck']['variationId']='red';save(other)
            self.assertEqual(len(json.loads(path.read_text())['observations']),2)
