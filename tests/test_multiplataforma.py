"""Verifica schema multi-vendor sem rede e sem modificar catálogo ML."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "integracoes/multiplataforma"))
from schema import CatalogError, build_catalog, from_legacy_ml, read_catalog, write_preview
from import_shopee import read_shopee_csv, parse_brl
from import_amazon import read_amazon_csv
from import_mercadolivre import read_mercadolivre_json
from merge import merge_catalogs

class MultiplataformaTests(unittest.TestCase):
    def test_registered_shopee_and_raw_csv(self):
        catalog = read_catalog(ROOT / "_data/produtos_unificados.json")
        self.assertEqual(len(catalog["products"]), 10)
        parsed = read_shopee_csv(ROOT / "_data/shopee_ofertas.csv")
        self.assertEqual(len(parsed["products"]), 10)
        original = {p["id"]: p["offers"][0] for p in catalog["products"]}
        for p in parsed["products"]:
            self.assertEqual(p["offers"][0]["affiliate_url"], original[p["id"]]["affiliate_url"])
            self.assertIsNone(p["offers"][0]["in_stock"])
            self.assertEqual(p["offers"][0]["price_status"], "unverified")

    def test_shopee_select_and_decimal(self):
        self.assertEqual(parse_brl("R$ 1.299,90"), 1299.9)
        subset = read_shopee_csv(ROOT / "_data/shopee_ofertas.csv", ["48360418130"])
        self.assertEqual(len(subset["products"]), 1)
        with self.assertRaises(CatalogError):
            read_shopee_csv(ROOT / "_data/shopee_ofertas.csv", ["9999999"])

    def test_links_never_become_trusted_by_default(self):
        p = read_catalog(ROOT / "_data/produtos_unificados.json")["products"][0]
        altered = json.loads(json.dumps(p))
        altered["offers"][0]["affiliate_url"] = "https://s.shopee.com.br.evil.example/x"
        with self.assertRaises(CatalogError):
            build_catalog([altered])
        altered = json.loads(json.dumps(p))
        altered["offers"][0]["price_status"] = "verified"
        with self.assertRaises(CatalogError):
            build_catalog([altered])

    def test_legacy_ml_adapter(self):
        old = {
            "id": "MLB123456789", "name": "Mouse modelo A",
            "category": "Periféricos", "price": 79.9,
            "affiliateUrl": "https://meli.la/Ab123CD", "imageUrl": "https://mlstatic.com/abc.webp",
        }
        normalized = from_legacy_ml(old)
        self.assertEqual(normalized["id"], "prod_ml_123456789")
        self.assertEqual(normalized["offers"][0]["platform"], "mercadolivre")
        self.assertIsNone(normalized["offers"][0]["in_stock"])
        self.assertEqual(normalized["image_url"], old["imageUrl"])
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "legacy.json"
            p.write_text(json.dumps({"products": [old]}), encoding="utf-8")
            self.assertEqual(len(read_mercadolivre_json(p)["products"]), 1)

    def test_amazon_requires_affiliate_tag(self):
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "amazon.csv"
            f.write_text("asin,title,affiliate_url,price\nB08N5WRWNW,Item,https://www.amazon.com.br/dp/B08N5WRWNW,199,90\n", encoding="utf-8")
            with self.assertRaises(CatalogError):
                read_amazon_csv(f)
            f.write_text("asin,title,affiliate_url,price\nB08N5WRWNW,Item,https://www.amazon.com.br/dp/B08N5WRWNW?tag=exemplo-20,\"199,90\"\n", encoding="utf-8")
            data = read_amazon_csv(f)
            self.assertEqual(len(data["products"]), 1)
            self.assertIsNone(data["products"][0]["offers"][0]["in_stock"])

    def test_multi_offer_explicit_id_mapping(self):
        ml = from_legacy_ml({"id":"MLB123456789","name":"Mouse A","category":"Periféricos","affiliateUrl":"https://meli.la/Ab123CD","price":79.9},universal_id="prod_mouse_a")
        sp = json.loads(json.dumps(read_catalog(ROOT / "_data/produtos_unificados.json")["products"][0]))
        sp["id"] = "prod_mouse_a"
        combined = merge_catalogs([build_catalog([ml]),build_catalog([sp])])
        self.assertEqual(len(combined["products"][0]["offers"]), 2)
        self.assertEqual(len(combined["products"]), 1)

    def test_no_overwrite_and_draft_articles(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "draft.json"
            write_preview(read_catalog(ROOT / "_data/produtos_unificados.json")["products"],path)
            with self.assertRaises(CatalogError):
                write_preview([],path)
        names = [
            "mouse-attack-shark-x11-dock-shopee","power-bank-mini-10000mah-usbc-lightning-shopee",
            "kit-gamer-7-pecas-celular-shopee","teclado-mecanico-60-switch-azul-shopee",
            "kit-teclado-semi-mecanico-mouse-rgb-shopee","suporte-dobravel-notebook-multiposicoes-shopee",
            "hub-usbc-hdmi-sd-variacoes-shopee","impressora-hp-2975-wifi-custo-cartucho-shopee",
            "mousepad-gamer-40x40-emborrachado-shopee","ring-light-12-polegadas-tripe-shopee",
        ]
        for name in names:
            content = (ROOT / "_artigos" / (name + ".md")).read_text(encoding="utf-8")
            self.assertIn('status: "rascunho"',content)
            self.assertIn('include link-shopee.html',content)
            self.assertIn("shopee_item_id:",content)

if __name__ == "__main__":
    unittest.main()
