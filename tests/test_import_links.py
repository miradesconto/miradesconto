import sys
import unittest
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'integracoes' / 'mercadolivre'))
from import_links import affiliate, allowed, prepare, parse_page, configured_sources

class ImportTest(unittest.TestCase):
    def test_affiliate_card_resolution(self):
        body = (Path(__file__).parent / 'fixtures/MLB2766771378.html').read_text()
        body = body.replace('Creatina 1kg Suplemento Monohidratada em pó 100% Pura - Soldiers Nutrition', 'Mouse Logitech G305')
        body = body.replace('<div class="poly-card">', '<div class="poly-card"><img src="https://http2.mlstatic.com/test.jpg">')
        # Perfil publico com recomendacoes nao e anuncio individual.
        with self.assertRaisesRegex(ValueError, 'Link abre perfil'):
            parse_page(body, 'https://www.mercadolivre.com.br/social/owner', 'https://meli.la/example')
        with self.assertRaisesRegex(ValueError, 'Link abre perfil'):
            parse_page(body + body.replace('MLB2766771378', 'MLB2766771379'),
                       'https://www.mercadolivre.com.br/social/owner', 'https://meli.la/example')
        # Uma lista identificada no caminho continua elegivel.
        rows = parse_page(body + body.replace('MLB2766771378', 'MLB2766771379'),
                          'https://www.mercadolivre.com.br/social/owner/lists/example', 'https://meli.la/example')
        self.assertEqual(len(rows), 2)
        self.assertEqual({r['id'] for r in rows}, {'MLB2766771378', 'MLB2766771379'})
        single_list = parse_page(body, 'https://www.mercadolivre.com.br/social/owner/lists/example', 'https://meli.la/example')
        self.assertEqual(len(single_list),1)
        self.assertEqual(single_list[0]['_observation']['price'], 68.90)
        self.assertEqual(single_list[0]['affiliateUrl'], 'https://meli.la/example')
        updated, archive = prepare({'products':[single_list[0]],'publishedIds':[], 'metadata':{'niche':'tech'}},[],
                                  ['https://meli.la/example'],datetime.now(timezone.utc),lambda link:single_list)
        self.assertEqual(len(updated['products']),1)
        self.assertEqual(archive,[])
        self.assertEqual(updated['metadata']['affiliateSources'],['https://meli.la/example'])

    def test_confirmed_primary_card_does_not_import_recommendations(self):
        body = (Path(__file__).parent / 'fixtures/MLB2766771378.html').read_text()
        body = body.replace(
            'Creatina 1kg Suplemento Monohidratada em pó 100% Pura - Soldiers Nutrition',
            'Fone QCY T13 ANC 2 Azul',
        )
        body = body.replace('<div class="poly-card">',
                            '<div class="poly-card"><img src="https://http2.mlstatic.com/test.jpg">')
        suggestions = body + body.replace('MLB2766771378', 'MLB2766771379')
        url = 'https://www.mercadolivre.com.br/social/owner'
        link = 'https://meli.la/abc'
        with self.assertRaisesRegex(ValueError, 'Link abre perfil'):
            parse_page(suggestions, url, link)
        selected = parse_page(suggestions, url, link, 'MLB2766771378')
        self.assertEqual(selected['id'], 'MLB2766771378')
        self.assertEqual(selected['affiliateUrl'], link)
        self.assertEqual(selected['_observation']['price'], 68.90)
        with self.assertRaisesRegex(ValueError, 'nao encontrado'):
            parse_page(suggestions, url, link, 'MLB9999999999')
        with self.assertRaisesRegex(ValueError, 'invalido'):
            parse_page(suggestions, url, link, 'INVALID')


    def test_explicit_model_matches_only_one_profile_card(self):
        from import_links import parse_page
        body = (Path(__file__).parent / 'fixtures/MLB2766771378.html').read_text()
        body = body.replace(
            'Creatina 1kg Suplemento Monohidratada em pó 100% Pura - Soldiers Nutrition',
            'Smart TV LG 43LR6700PSA Full HD',
        )
        body = body.replace('<div class="poly-card">',
                            '<div class="poly-card"><img src="https://http2.mlstatic.com/test.jpg">')
        profile='https://www.mercadolivre.com.br/social/profile'
        link='https://meli.la/example'
        selected = parse_page(body,profile,link,expected_title_tokens=['lg','43lr6700'])
        self.assertEqual(selected['id'],'MLB2766771378')
        self.assertEqual(selected['affiliateUrl'],link)
        self.assertEqual(selected['_observation']['price'],68.90)
        with self.assertRaisesRegex(ValueError,'nao encontrado'):
            parse_page(body,profile,link,expected_title_tokens=['samsung','qled'])
        doubled = body + body.replace('MLB2766771378','MLB2766771379')
        with self.assertRaisesRegex(ValueError,'nao encontrado'):
            parse_page(doubled,profile,link,expected_title_tokens=['lg','43lr6700'])
        with self.assertRaisesRegex(ValueError,'Link abre perfil'):
            parse_page(body,profile,link)

    def test_configured_list_replaces_old_discovery_source(self):
        import tempfile,json
        current={'metadata':{'affiliateSources':['https://meli.la/old']}}
        with tempfile.TemporaryDirectory() as folder:
            file=Path(folder)/'lists.json'
            file.write_text(json.dumps({'links':['https://meli.la/new']}))
            self.assertEqual(configured_sources(current,file),['https://meli.la/new'])
            self.assertEqual(current['metadata']['affiliateSources'],['https://meli.la/old'])


    def test_submitted_models_must_match_real_listing(self):
        from import_links import title_matches_requested, resolve_requested
        self.assertTrue(title_matches_requested('Smart TV LG 43LR6700PSA FULL HD', ['lg', '43lr6700']))
        self.assertTrue(title_matches_requested('Caixa Som Kapbom KA-8596', ['kapbom', '8596']))
        self.assertTrue(title_matches_requested('Mini Drone E88 Pro com Câmera Wi-Fi', ['drone', 'e88']))
        self.assertFalse(title_matches_requested('Smart TV Samsung 43 Polegadas', ['lg', '43lr6700']))
        self.assertFalse(title_matches_requested('Drone Sem Marca', ['drone', 'e88']))
        self.assertFalse(title_matches_requested('Caixa de som Bluetooth de outra marca', ['aiwa', 'bbs']))
        from tech_policy import category
        self.assertEqual(category({'name':'Controle Remoto Compatível Com Aoc Smart Tv'}), 'TVs e projetores')
        self.assertEqual(category({'name':'Mini Drone E88 Pro Com Câmera Wifi'}), 'Gaming')

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
