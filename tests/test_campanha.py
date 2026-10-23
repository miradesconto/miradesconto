import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'integracoes'))
from campanha import validate_extras, render, ROOT
class CampaignTests(unittest.TestCase):
    def sample(self):
        return dict(id='AMZ-produto-teste',name='Produto teste',store='Amazon',category='Áudio',affiliateUrl='https://amzn.to/Teste',imageUrl='https://m.media-amazon.com/images/I/test.jpg',productUrl='https://www.amazon.com.br/dp/B012345678',affiliateVerified=True,affiliateLinkType='product')
    def test_verification_and_duplicate(self):
        p=self.sample()
        self.assertEqual(validate_extras([p],[]),[p])
        for change in ({'affiliateVerified':False},{'affiliateUrl':'https://amazon.com.br.evil.test/a'},{'store':'Shopee'},{'price':100}):
            with self.assertRaises(ValueError):validate_extras([dict(p,**change)],[])
        with self.assertRaises(ValueError):validate_extras([p,p],[])
    def test_destinations_specific_and_reproducible(self):
        files=render(ROOT)
        import json
        pins=json.loads(files['docs/pinterest-destinos.json'])
        self.assertGreater(len(pins),40)
        self.assertTrue(all(p["id"] != "MLB4562931826" for p in pins))
        self.assertEqual(len({p['destination'] for p in pins}),len(pins))
        self.assertTrue(all('/oferta/' in p['destination'] and 'utm_source=pinterest' in p['destination'] for p in pins))
        self.assertEqual(files,render(ROOT))

    def test_generation_preserves_primary_catalog_shards(self):
        import tempfile
        import shutil
        from campanha import generate
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)
            for folder in ('dados','_data','_artigos','catalogo'):
                shutil.copytree(ROOT/folder,target/folder)
            before={p.name:p.read_bytes() for p in (target/'catalogo').glob('produtos-*.json')}
            generate(root=target)
            self.assertEqual(before,{p.name:p.read_bytes() for p in (target/'catalogo').glob('produtos-*.json')})
