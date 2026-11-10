"""Regressão do visual premium Shopee: fonte oficial, destaque + 4 achados."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ShopeePremiumTest(unittest.TestCase):
    def test_product_source_has_feature_and_four_categories(self):
        data = json.loads((ROOT / "_data/shopee_gamer_publicados.json").read_text())
        self.assertTrue(data)
        self.assertTrue(any(p.get("keyword") == "monitor gamer 144hz" for p in data))
        keywords = ("headset gamer", "mouse gamer sem fio",
                    "teclado mecanico switch red", "ssd nvme 1tb")
        for keyword in keywords:
            with self.subTest(keyword=keyword):
                self.assertTrue(any(p.get("keyword") == keyword for p in data))

    def test_showcase_uses_api_data_and_valid_affiliate_links(self):
        page = (ROOT / "_includes/shopee-destaques.html").read_text()
        for term in ("site.data.shopee_gamer_publicados", "shopee-feature",
                     "shopee-finds-grid", "shown < 4", "shopee_primary.affiliate_url",
                     "item.affiliate_url", "sponsored nofollow noopener noreferrer",
                     "site.data.shopee_fotos_locais", "Foto em atualização"):
            with self.subTest(term=term):
                self.assertIn(term, page)

    def test_frontend_keeps_ml_separate_and_assets_available(self):
        home = (ROOT / "index.html").read_text()
        script = (ROOT / "ofertas-automaticas.js").read_text()
        css = (ROOT / "shopee-destaques.css").read_text()
        self.assertIn('title="Na mira da Shopee"', home)
        self.assertIn('shopee-destaques.css?v=2', home)
        self.assertIn('shopee-premium.js?v=1', home)
        self.assertIn("ml.length ? ml.slice(0, 6) : shop.slice(0, 6)", script)
        self.assertIn(".shopee-feature-photo", css)
        self.assertIn(".shopee-finds-grid", css)
        self.assertIn('data-mira-layout="gamer"', css)
        self.assertIn("mirror_curated_shopee", (ROOT / "integracoes/automacao/cache_imagens_ofertas.py").read_text())


if __name__ == "__main__":
    unittest.main()
