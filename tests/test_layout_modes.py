"""Regressão: Clássico/Gamer são temas de uma mesma homepage."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class LayoutModesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.home = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.legacy = (ROOT / "gamer.html").read_text(encoding="utf-8")
        cls.script = (ROOT / "modo-visual.js").read_text(encoding="utf-8")
        cls.styles = (ROOT / "modo-visual.css").read_text(encoding="utf-8")

    def test_classico_preserva_estrutura_integral(self):
        for marker in (
            'rel="canonical"',
            'id="searchInput"',
            'id="productList"',
            'id="sortSelect"',
            'id="loadMore"',
            'id="hero-product-seeds"',
            'vitrine-diaria.html',
            'id="shareStatus"',
            'analytics.js',
            'site.artigos',
            'interface.js',
            'carrossel.js',
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.home)

    def test_seletor_usa_mesma_pagina_sem_reload(self):
        for marker in ('data-mira-layout="classic"', 'mira-mode-switch',
                       'data-layout-option="classic"', 'data-layout-option="gamer"',
                       'href="?modo=classic"', 'href="?modo=gamer"',
                       'modo-visual.js?v=2', 'modo-visual.css?v=3'):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.home)
        for marker in ('event.preventDefault()', "html.setAttribute('data-mira-layout'",
                       "localStorage.setItem", "link.addEventListener('click'",
                       "window.history.replaceState"):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.script)
        self.assertNotIn('window.location.replace', self.script)
        self.assertNotIn("'gamer.html'", self.script)

    def test_same_content_just_changes_theme(self):
        self.assertIn('[data-mira-layout="gamer"]', self.styles)
        self.assertIn('[data-mira-layout="classic"]', self.styles)
        self.assertNotIn('display:none', self.styles.replace(' ', '').lower())
        self.assertIn('id="productList"', self.home)
        self.assertNotIn('gamer.js?v=', self.home)

    def test_link_antigo_redireciona_para_home_em_gamer(self):
        self.assertIn('url=/?modo=gamer', self.legacy)
        self.assertIn("window.location.replace('/?modo=gamer')", self.legacy)
        self.assertIn('noindex,follow', self.legacy)

    def test_feed_existe_e_estrutura_valida(self):
        data = json.loads((ROOT / 'api/produtos.json').read_text(encoding='utf-8'))
        self.assertTrue(data)
        for item in data[:10]:
            self.assertTrue({'titulo', 'preco_atual', 'imagem', 'link_afiliado', 'loja'} <= set(item))


if __name__ == '__main__':
    unittest.main()
