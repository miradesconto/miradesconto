import importlib.util
import json
from pathlib import Path
import tempfile
from unittest.mock import Mock, patch
import unittest
from datetime import datetime,timezone,timedelta
import requests

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('radar_remote',ROOT/'integracoes/automacao/gerar_radar.py')
radar=importlib.util.module_from_spec(spec);spec.loader.exec_module(radar)

class RadarRemoteTests(unittest.TestCase):
    def setup_files(self,root):
        now=datetime(2026,10,10,tzinfo=timezone.utc);item='MLB1234567890'
        p={'id':item,'name':'Produto','category':'Celulares','price':70,'oldPrice':100,
           'affiliateUrl':'https://meli.la/individual','imageUrl':'https://example.org/image.png',
           'priceCheck':{'method':'poly-card-v1','status':'verified','price':70,'checkedAt':now.isoformat()}}
        catalog=root/'catalogo.json';catalog.write_text(json.dumps({'products':[p],'publishedIds':[item]}))
        output=root/'radar.json';output.write_text('{"generatedAt":"2026-01-01T00:00:00Z"}\n')
        data={'schemaVersion':1,'productId':item,'currency':'BRL','observations':[
            {'at':(now-timedelta(days=i)).isoformat(),'price':100,'itemId':item,'variationId':None,'method':'poly-card-v1'} for i in range(1,10)]}
        return catalog,output,data

    def test_remote_radar_reads_Worker_and_does_not_require_local_history(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);catalog,output,data=self.setup_files(root);session=Mock()
            session.get.return_value.status_code=200;session.get.return_value.json.return_value=data
            with patch.object(radar,'CATALOG',catalog),patch.object(radar,'OUTPUT',output),patch.object(radar,'HISTORY',root/'missing'),\
                    patch.dict('os.environ',{'MIRA_HISTORY_BASE_URL':'https://worker.example'}),patch.object(radar.requests,'Session',return_value=session):
                self.assertEqual(radar.main(),0)
            result=json.loads(output.read_text());self.assertEqual(result['eligibleCount'],1)
            self.assertEqual(result['featuredCount'],1)
            self.assertEqual(session.get.call_args.args[0],'https://worker.example/api/history/MLB1234567890')
            self.assertFalse(session.get.call_args.kwargs['allow_redirects'])

    def test_global_failure_keeps_previous_timestamp_and_stops_after_first_request(self):
        for status in [429,503]:
            with tempfile.TemporaryDirectory() as temp:
                root=Path(temp);catalog,output,_=self.setup_files(root);before=output.read_bytes();session=Mock()
                session.get.return_value.status_code=status
                with patch.object(radar,'CATALOG',catalog),patch.object(radar,'OUTPUT',output),\
                        patch.dict('os.environ',{'MIRA_HISTORY_BASE_URL':'https://worker.example'}),patch.object(radar.requests,'Session',return_value=session):
                    self.assertEqual(radar.main(),0)
                self.assertEqual(output.read_bytes(),before);self.assertEqual(session.get.call_count,1)

    def test_network_failure_does_not_replace_previous_radar(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);catalog,output,_=self.setup_files(root);before=output.read_bytes();session=Mock()
            session.get.side_effect=requests.RequestException('network unavailable')
            with patch.object(radar,'CATALOG',catalog),patch.object(radar,'OUTPUT',output),\
                    patch.dict('os.environ',{'MIRA_HISTORY_BASE_URL':'https://worker.example'}),patch.object(radar.requests,'Session',return_value=session):
                self.assertEqual(radar.main(),0)
            self.assertEqual(output.read_bytes(),before)

if __name__=='__main__':unittest.main()
