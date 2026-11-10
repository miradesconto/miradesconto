"""Regressão da seleção Shopee e dos pontos de acesso nas páginas comerciais."""
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

    def test_dedicated_page_uses_api_data_and_cached_images(self):
        page = (ROOT / "shopee-gamer/index.html").read_text()
        for term in ("site.data.shopee_gamer_publicados", "site.data.shopee_fotos_locais",
                     "item.affiliate_url", "sponsored nofollow noopener noreferrer",
                     "Consulte o preço na Shopee"):
            with self.subTest(term=term):
                self.assertIn(term, page)

    def test_commercial_pages_link_to_selection_without_extra_grids(self):
        entry = (ROOT / "_includes/shopee-entry.html").read_text()
        self.assertIn("site.data.shopee_gamer_publicados.size > 0", entry)
        self.assertIn("/shopee-gamer/", entry)
        for name in ("index.html", "catalogo/index.html", "black-friday/index.html", "radar/index.html"):
            with self.subTest(name=name):
                page = (ROOT / name).read_text()
                self.assertIn("include shopee-entry.html", page)
                self.assertNotIn("include shopee-destaques.html", page)


if __name__ == "__main__":
    unittest.main()
