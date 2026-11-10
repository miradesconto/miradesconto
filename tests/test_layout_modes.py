"""Regressão das duas apresentações: preservar o site original e o feed compartilhado."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class LayoutModesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.home = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.gamer = (ROOT / "gamer.html").read_text(encoding="utf-8")
        cls.gamer_js = (ROOT / "gamer.js").read_text(encoding="utf-8")
        cls.preference = (ROOT / "modo-visual.js").read_text(encoding="utf-8")

    def test_classico_preserva_estrutura_integral(self):
        for marker in (
            'rel="canonical"',
            'id="searchInput"',
            'id="productList"',
            'id="sortSelect"',
            'id="loadMore"',
            'id="auto-ofertas"',
            'vitrine-diaria.html',
            'id="shareStatus"',
            'analytics.js',
            'site.artigos',
            'interface.js',
            'carrossel.js',
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.home)

    def test_alternador_bidirecional(self):
        for file in (self.home, self.gamer):
            for marker in ('mira-mode-switch', 'data-layout-option="classic"', 'data-layout-option="gamer"',
                           'href="gamer.html"', 'href="./"', 'modo-visual.js?v=1'):
                with self.subTest(marker=marker):
                    self.assertIn(marker, file)
        self.assertIn('localStorage.setItem', self.preference)
        self.assertIn("read() === 'gamer'", self.preference)

    def test_gamer_reusa_feed_e_trata_falhas(self):
        for marker in ("fetch('/api/produtos.json'", 'try {', 'catch (_)', 'response.ok',
                       "document.createElement", 'rel = ', "noopener noreferrer",
                       'Number.isFinite', "new Intl.NumberFormat('pt-BR'", 'gamer-more'):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.gamer_js)
        self.assertNotIn("innerHTML +=", self.gamer_js)
        self.assertNotIn('fetch("/api/', self.home)
        self.assertIn('id="vitrine-produtos"', self.gamer)

    def test_feed_existe_e_estrutura_valida(self):
        import json
        data = json.loads((ROOT / 'api/produtos.json').read_text(encoding='utf-8'))
        self.assertTrue(data)
        for item in data[:10]:
            self.assertTrue({'titulo','preco_atual','imagem','link_afiliado','loja'} <= set(item))


if __name__ == '__main__':
    unittest.main()
