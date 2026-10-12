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
    def test_blog_has_shop_link_alongside_article_link(self):
        text=(ROOT/"blog/index.html").read_text(encoding="utf-8")
        self.assertEqual(text.count("editorial-shop-cta"),3)
        self.assertEqual(text.count("blog-shopee-card"),3)
        self.assertEqual(text.count("editorial-card-affiliate"),3)
        self.assertEqual(text.count('rel="sponsored nofollow noopener noreferrer"'),3)
    def test_button_is_styled_and_affiliation_clear(self):
        snippet=(ROOT/"_includes/link-shopee.html").read_text(encoding="utf-8")
        self.assertIn("shopee-cta-button",snippet)
        self.assertIn("Link de afiliado",snippet)
        self.assertIn("data-item-id",snippet)
        self.assertIn('rel="sponsored nofollow noopener noreferrer"',snippet)
        css=(ROOT/"blog/artigo.css").read_text(encoding="utf-8")
        self.assertIn(".article-body .shopee-cta-button",css)
        self.assertIn(".article-body .shopee-cta-button:focus-visible",css)
