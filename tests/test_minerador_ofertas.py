"""Testes independentes das credenciais dos marketplaces."""
import hashlib
import importlib.util
import json
import os
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
# O workflow geral não instala requests/PyGithub/dotenv.
# O workflow dedicado instala e EXECUTA estes testes; aqui pulamos sem contaminar outros módulos.
try:
    import requests
    import github
    import dotenv
except ModuleNotFoundError as exc:
    raise unittest.SkipTest("Dependências do minerador validadas no workflow dedicado") from exc

ROOT = Path(__file__).resolve().parents[1]
file = ROOT / 'integracoes/automacao/minerador_ofertas.py'
spec = importlib.util.spec_from_file_location('minerador_test', file)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class FakeResponse:
    def __init__(self, data):
        self.data = data
    def raise_for_status(self):
        pass
    def json(self):
        return self.data


class FakeSession:
    def __init__(self):
        self.calls = []
    def post(self, url, **kw):
        self.calls.append(('POST', url))
        if url == m.SHOPEE_URL:
            body = kw['data']
            auth = kw['headers']['Authorization']
            credentials = auth.replace('SHA256 ', '').split(', ')
            fields = dict(part.split('=', 1) for part in credentials)
            signature = hashlib.sha256(b'app' + fields['Timestamp'].encode() + body + b'secret').hexdigest()
            assert signature == fields['Signature']
            return FakeResponse({'data': {'productOfferV2': {'nodes': [
                {'productName': 'Mouse Gamer RGB USB', 'priceMin': '239.90',
                 'imageUrl': 'https://img.shopee.test/mouse.webp',
                 'offerLink': 'https://s.shopee.com.br/a123'}
            ]}}})
        if url == m.BOT_URL_DEFAULT:
            assert kw['headers']['X-API-Key'] == 'bot-secret'
            return FakeResponse({'success': True, 'data': {
                'final_url': 'https://meli.la/Afi222',
                'product': {'title': 'Notebook Gamer RTX 4060', 'price': 4299.9,
                            'image_url': 'https://mlstatic.com/notebook.webp'}
            }})
        raise AssertionError(f'POST inesperado: {url}')
    def get(self, url, **kw):
        self.calls.append(('GET', url))
        assert url == m.ML_SEARCH
        return FakeResponse({'results': [
            {'title':'Notebook RTX 4060', 'permalink':'https://www.mercadolivre.com.br/produto/p/MLB999',
             'thumbnail':'https://mlstatic.com/notebook.webp'}
        ]})


class MineradorTest(unittest.TestCase):
    def test_normalizacao_preco_e_link(self):
        a = m.normalize('Mouse', 'R$ 1.299,90', 'https://cdn.test/x.jpg', 'https://meli.la/abc','Mercado Livre')
        self.assertEqual(a['preco_atual'],1299.90)
        self.assertEqual(list(a), list(m.FIELDS))
        self.assertIsNone(m.normalize('Mouse', 9, 'http://cdn.test/x.jpg', 'https://meli.la/abc','Mercado Livre'))
        self.assertIsNone(m.normalize('Mouse', 9, 'https://cdn.test/x.jpg', 'https://meli.la/1NguveN','Mercado Livre'))
        self.assertIsNone(m.normalize('Mouse', 9, 'https://cdn.test/x.jpg', 'https://www.mercadolivre.com.br/item/p/MLB99','Mercado Livre'))

    def test_shopee_assinatura_e_tracking(self):
        with patch.dict(os.environ, {'SHOPEE_APP_ID':'app','SHOPEE_APP_SECRET':'secret'}):
            rows, ok = m.mine_shopee(FakeSession(), ('mouse',))
        self.assertTrue(ok)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['loja'],'Shopee')
        self.assertEqual(rows[0]['link_afiliado'],'https://s.shopee.com.br/a123')

    def test_shopee_retry_em_erro_10000(self):
        class RetrySession(FakeSession):
            attempt = 0
            def post(self, url, **kwargs):
                self.attempt += 1
                if self.attempt == 1:
                    return FakeResponse({'errors': [{'extensions': {'code': 10000}}]})
                return super().post(url, **kwargs)
        session = RetrySession()
        with patch.object(m.time, 'sleep', return_value=None):
            response = m.shopee_request(session, 'app', 'secret', 'query { productOfferV2 { nodes { itemId } } }')
        self.assertIn('productOfferV2', response)
        self.assertEqual(session.attempt, 2)

    def test_busca_mercado_livre_e_bot(self):
        with patch.dict(os.environ, {'BOT_API_KEY':'bot-secret'}):
            rows, ok = m.mine_ml_bot(FakeSession(),('rtx 4060',))
        self.assertTrue(ok)
        self.assertEqual(rows[0]['preco_atual'],4299.9)
        self.assertEqual(rows[0]['link_afiliado'],'https://meli.la/Afi222')

    def test_radar_verificado(self):
        radar = json.loads((ROOT / '_data/radar.json').read_text())
        first = next(p for p in radar['byId'].values() if p.get('checkedAt'))
        after = datetime.fromisoformat(first['checkedAt'].replace('Z','+00:00')) + timedelta(minutes=30)
        result = m.verified_radar(now=after)
        self.assertTrue(all(x['loja']=='Mercado Livre' for x in result))
        self.assertTrue(all(x['link_afiliado'].startswith('https://') for x in result))

    def test_falha_nao_apaga_anuncios(self):
        row = m.normalize('Mouse',100,'https://cdn.test/a.png','https://meli.la/def','Mercado Livre')
        got = m.merge_items([], [], [row], shopee_ok=False,ml_ok=False)
        self.assertEqual(got,[row])
        got = m.merge_items([row], [row], [], shopee_ok=True, ml_ok=True)
        self.assertEqual(len(got),1)

    def test_shopee_parcial_publica_resultados_validos_e_intercala(self):
        shop = m.normalize('Headset USB', 120, 'https://img.shopee.com/1.jpg', 'https://s.shopee.com.br/xyz', 'Shopee')
        ml = m.normalize('Monitor Gamer', 799, 'https://img.mlstatic.com/1.jpg', 'https://meli.la/xyz', 'Mercado Livre')
        out = m.merge_items([shop], [ml], [], shopee_ok=False, ml_ok=True)
        self.assertEqual([x['loja'] for x in out], ['Shopee', 'Mercado Livre'])
        out2 = m.merge_items([], [ml], [shop], shopee_ok=False, ml_ok=True)
        self.assertEqual([x['loja'] for x in out2], ['Shopee', 'Mercado Livre'])

    def test_nicho_exclui_mochilas_e_bolsas(self):
        self.assertFalse(m.is_tech('Mochila Grande Reforçada para Notebook'))
        self.assertFalse(m.is_tech('Bolsa Reforçada para Notebook 15'))
        self.assertTrue(m.is_tech('Notebook Acer Ryzen 5 com SSD 512GB'))
        self.assertTrue(m.is_tech('Dissipador SSD M.2 NVMe'))

    def test_preserva_produto_shopee_com_foto_local(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "assets/ofertas").mkdir(parents=True)
            name = "a" * 24 + ".jpg"
            (root / "assets/ofertas" / name).write_bytes(b"jpeg_local")
            feed = root / "api/produtos.json"
            feed.parent.mkdir()
            row = {
                "titulo": "Fone Bluetooth Shopee",
                "preco_atual": 49.90,
                "imagem": "/assets/ofertas/" + name,
                "link_afiliado": "https://s.shopee.com.br/abcDEF",
                "loja": "Shopee"
            }
            feed.write_text(json.dumps([row]), encoding="utf-8")
            with patch.object(m, "ROOT", root):
                preserved = m.previous_items(feed)
            self.assertEqual(preserved, [row])

    def test_feed_e_home_estao_conectados(self):
        data = json.loads((ROOT / 'api/produtos.json').read_text(encoding='utf-8'))
        self.assertGreaterEqual(len(data),4)
        self.assertEqual(set(data[0]),set(m.FIELDS))
        html = (ROOT/'index.html').read_text(encoding='utf-8')
        self.assertIn('id="hero-product-seeds"', html)
        self.assertIn('site.data.ofertas_automaticas', html)

if __name__ == '__main__':
    unittest.main()
