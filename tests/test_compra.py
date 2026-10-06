import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class PurchaseContentTest(unittest.TestCase):
    def test_curated_data_matches_catalog_and_official_links(self):
        catalog={p['id']:p for p in json.loads((ROOT/'dados/catalogo.json').read_text(encoding='utf-8'))['products']}
        lists=json.loads((ROOT/'integracoes/mercadolivre/listas-afiliadas.json').read_text(encoding='utf-8'))['links']
        curated=json.loads((ROOT/'_data/compra_products.json').read_text(encoding='utf-8'))
        for id,p in curated.items():
            for key in ('name','imageUrl','affiliateUrl','category'):
                self.assertEqual(p[key],catalog[id].get(key,''),(id,key))
            self.assertEqual(p['list'],p['affiliateUrl'] in lists)
            self.assertNotIn('price',p,'Prices must come from live generated catalog, never editorial snapshots')

    def test_ten_unique_useful_pages(self):
        files=list((ROOT/'_compras').glob('*.md'))
        self.assertEqual(len(files),10)
        paths=set()
        for file in files:
            _,front,body=file.read_text(encoding='utf-8').split('---',2)
            meta={k:json.loads(v) for k,v in (line.split(': ',1) for line in front.strip().splitlines())}
            self.assertNotIn(meta['permalink'],paths)
            paths.add(meta['permalink'])
            self.assertGreater(len(body.split()),230,file.name)
            self.assertGreaterEqual(body.count('## '),4)
            self.assertIn('relative_url',body)

if __name__=='__main__': unittest.main()
