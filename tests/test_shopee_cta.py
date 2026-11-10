"""Testa CTAs e rotulagem publicitária dos três artigos Shopee."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
SLUGS=("mouse-attack-shark-x11-dock-shopee","power-bank-mini-10000mah-usbc-lightning-shopee","kit-gamer-7-pecas-celular-shopee")
class ShopeeCtaTests(unittest.TestCase):
    def test_early_and_end_purchase_cta(self):
        for slug in SLUGS:
            text=(ROOT/"_artigos"/(slug+".md")).read_text(encoding="utf-8")
            self.assertEqual(text.count("include link-shopee.html"),2)
            self.assertLess(text.index('placement="top"'),text.index("include foto-shopee.html"))
            self.assertIn('class="shopee-disclosure"',text)
            self.assertIn("Publicidade:",text)
            self.assertIn('status: "publicado"',text)
    def test_blog_landing_links_to_articles_without_shopping_cards(self):
        text = (ROOT / "blog/index.html").read_text(encoding="utf-8")
        self.assertIn('entry.url | relative_url', text)
        for marker in ("editorial-shop-cta", "editorial-card-affiliate", "shopee-destaques.html",
                       "shopee-entry.html", "vitrine-diaria.html"):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, text)
    def test_button_is_styled_and_affiliation_clear(self):
        snippet=(ROOT/"_includes/link-shopee.html").read_text(encoding="utf-8")
        self.assertIn("shopee-cta-button",snippet)
        self.assertIn("Link de afiliado",snippet)
        self.assertIn("data-item-id",snippet)
        self.assertIn('rel="sponsored nofollow noopener noreferrer"',snippet)
        css=(ROOT/"blog/artigo.css").read_text(encoding="utf-8")
        self.assertIn(".article-body .shopee-cta-button",css)
        self.assertIn(".article-body .shopee-cta-button:focus-visible",css)
