"""Regressão da campanha Black Friday 2026."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BlackFridayCampaignTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ids = json.loads((ROOT / "_data/black_friday.json").read_text())["selectedIds"]
        cls.offers = json.loads((ROOT / "_data/ofertas_site.json").read_text())
        cls.images = json.loads((ROOT / "_data/black_friday_images.json").read_text())

    def test_selection_has_20_distinct_registered_products(self):
        self.assertEqual(len(self.ids), 20)
        self.assertEqual(len(set(self.ids)), 20)
        for id in self.ids:
            with self.subTest(id=id):
                p = self.offers[id]
                self.assertTrue(p["affiliateUrl"].startswith("https://"))
                self.assertTrue(p["imageUrl"].startswith(("https://", "/assets/")))

    def test_local_images_exist_and_are_mapped_to_real_products(self):
        self.assertTrue(set(self.images).issubset(set(self.ids)))
        for id, image in self.images.items():
            with self.subTest(id=id):
                self.assertTrue(image.startswith("/assets/ofertas/"))
                self.assertTrue((ROOT / image.lstrip("/")).is_file())

    def test_campaign_disclaims_unverified_price(self):
        html = (ROOT / "black-friday/index.html").read_text()
        self.assertIn("Estar aqui não significa menor preço", html)
        self.assertIn("campaign_image", html)
        self.assertIn("Publicidade · Link de afiliado", html)

    def test_new_articles_have_local_cover(self):
        from importlib.util import module_from_spec, spec_from_file_location
        path = ROOT / "integracoes/automacao/check_blog_covers.py"
        spec = spec_from_file_location("blog_cover_gate", path)
        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        for slug in ("black-friday-2026-notebooks-o-que-conferir",
                     "black-friday-2026-achadinhos-setup-shopee"):
            with self.subTest(slug=slug):
                self.assertTrue(module.validate_one(ROOT / "_artigos" / (slug + ".md")).startswith("/assets/"))


if __name__ == "__main__":
    unittest.main()
