import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

import sys
sys.path.insert(0,str(ROOT/'integracoes'))
import catalogo

class PurchaseContentTest(unittest.TestCase):
    def test_shared_list_destinations_identify_each_product(self):
        data=catalogo.public_data(catalogo.load())
        shared=[p for p in data['products'] if p['affiliateUrl']=='https://meli.la/1NguveN']
        self.assertGreater(len(shared),1)
        self.assertEqual(len({p['offerUrl'] for p in shared}),len(shared))
        for p in shared:
            self.assertEqual(p['offerUrl'],p['productUrl'])
            self.assertEqual(catalogo.exact_offer_url(p),p['offerUrl'])
        p=dict(shared[0])
        p['productUrl']=p['productUrl'].replace('wid='+p['id'],'wid=MLB0000000000')
        self.assertIsNone(catalogo.exact_offer_url(p))
        p.update(registrationSource='affiliate-panel',productUrl='https://www.mercadolivre.com.br/notebook/p/MLB123#wid='+p['id']+'&source=lists&tracking_id=7a00916c-b4c9-43d3-8d80-d9a2d51aac01')
        self.assertEqual(catalogo.exact_offer_url(p),p['productUrl'])
        p['productUrl']=p['productUrl'].replace('7a00916c-b4c9-43d3-8d80-d9a2d51aac01','invalid')
        self.assertIsNone(catalogo.exact_offer_url(p))
        p['productUrl']='https://example.org/?wid='+p['id']+'&matt_tool_id=29904275'
        self.assertIsNone(catalogo.exact_offer_url(p))

    def test_curated_data_matches_catalog_and_official_links(self):
        catalog={p['id']:p for p in json.loads((ROOT/'dados/catalogo.json').read_text(encoding='utf-8'))['products']}
        lists=json.loads((ROOT/'integracoes/mercadolivre/listas-afiliadas.json').read_text(encoding='utf-8'))['links']
        curated=json.loads((ROOT/'_data/compra_products.json').read_text(encoding='utf-8'))
        for id,p in curated.items():
            for key in ('name','imageUrl','affiliateUrl','category'):
                self.assertEqual(p[key],catalog[id].get(key,''),(id,key))
            self.assertEqual(p['list'],p['affiliateUrl'] in lists or p['affiliateUrl']=='https://meli.la/1NguveN')
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
