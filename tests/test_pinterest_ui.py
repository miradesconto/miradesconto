import http.client
from http.server import HTTPServer
from pathlib import Path
import re
import sys
import threading
import unittest
from unittest.mock import patch
from urllib.parse import urlencode, urlsplit, parse_qs

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'integracoes/pinterest'))
import oauth_ui as ui


class LocalUITests(unittest.TestCase):
    def setUp(self):
        with patch.object(ui, 'HTTPServer', side_effect=lambda address, handler: HTTPServer(('127.0.0.1',0),handler)):
            self.server=ui.create_server()
        self.worker=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.worker.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.worker.join()

    def call(self, method, path, body=None, host='localhost:8765', origin=ui.ORIGIN):
        conn=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
        conn.request(method,path,body,{'Host':host,'Origin':origin,'Content-Type':'application/x-www-form-urlencoded'})
        response=conn.getresponse()
        result=(response.status,dict(response.getheaders()),response.read().decode())
        conn.close()
        return result

    def test_rejects_untrusted_host_and_cross_origin_forms(self):
        self.assertEqual(self.call('GET','/',host='attacker.invalid')[0],403)
        self.assertEqual(self.call('POST','/start','secret=FAKE',origin='https://attacker.invalid')[0],403)
        self.assertEqual(self.call('POST','/start','secret=FAKE&csrf=bad')[0],400)
        self.assertEqual(self.call('GET','/callback?code=FAKE&state=bad')[0],400)

    def test_oauth_exchange_single_use_and_clean_redirect(self):
        status,headers,body=self.call('GET','/')
        self.assertEqual(headers['Cache-Control'],'no-store')
        csrf=re.search(r'name="csrf" value="([^"]+)"',body)[1]
        status,headers,body=self.call('POST','/start',urlencode({'csrf':csrf,'secret':'FAKE-SECRET'}))
        self.assertEqual(status,303)
        self.assertNotIn('FAKE-SECRET',headers['Location'])
        state=parse_qs(urlsplit(headers['Location']).query)['state'][0]
        callback='/callback?'+urlencode({'state':state,'code':'FAKE-CODE'})
        with patch.object(ui.oauth,'exchange_code',return_value={'access_token':'FAKE-TOKEN'}) as exchange, patch.object(ui.oauth,'store_private') as save:
            status,headers,body=self.call('GET',callback)
            self.assertEqual(status,303)
            self.assertEqual(headers['Location'],'/done')
            exchange.assert_called_once_with('FAKE-CODE','FAKE-SECRET')
            save.assert_called_once()
            self.assertEqual(self.call('GET',callback)[0],400)
            self.assertNotIn('FAKE-TOKEN',self.call('GET','/done')[2])
