"""Controle dos três artigos Shopee publicados, sem interferir no catálogo ML."""
import csv
from pathlib import Path
import re
import unittest
ROOT=Path(__file__).resolve().parents[1]
EXPECTED={
 "mouse-attack-shark-x11-dock-shopee":("48360418130","https://s.shopee.com.br/W7NNInjzy","cn-11134207-820l4-mmh5v8n2m6f4e2"),
 "power-bank-mini-10000mah-usbc-lightning-shopee":("22499247158","https://s.shopee.com.br/1BN4AWlCe2","sg-11134201-81zvk-mik9ovwbhszk62"),
 "kit-gamer-7-pecas-celular-shopee":("19299299965","https://s.shopee.com.br/5AtCvsVyWw","br-11134207-7r98o-m32g7d6pp4ib32")
}
class PublishedShopeeTests(unittest.TestCase):
 def test_csv_and_published_articles(self):
  with (ROOT/"_data/shopee_ofertas.csv").open(encoding="utf-8",newline="") as f:
   rows={r["item_id"]:r for r in csv.DictReader(f)}
  self.assertEqual(set(rows),{v[0] for v in EXPECTED.values()})
  for slug,(item,url,image) in EXPECTED.items():
   row=rows[item]
   self.assertEqual(row["affiliate_url"],url)
   self.assertIn(image,row["image_url"])
   article=(ROOT/"_artigos"/(slug+".md")).read_text(encoding="utf-8")
   front=article.split("---",2)[1]
   self.assertIn('status: "publicado"',front)
   self.assertIn('published: true',front)
   self.assertIn('shopee_item_id: "'+item+'"',front)
   self.assertIn('affiliate_url: "'+url+'"',front)
   self.assertIn(image,front)
   self.assertIn('{% include link-shopee.html item_id=page.shopee_item_id %}',article)
   self.assertIn('{% include foto-shopee.html %}',article)
 def test_no_shopee_additions_to_ml_catalog(self):
  for path in (ROOT/"catalogo").glob("produtos-*.json"):
   self.assertNotIn('"platform":"shopee"',path.read_text(encoding="utf-8"))
