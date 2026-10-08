import unittest
from integracoes.social import gerar_pauta as gp


class SocialPipelineTests(unittest.TestCase):
    def test_angle_uses_observed_history(self):
        self.assertIn("Menor preço observado", gp.angle({"label": "Menor observado", "deltaAveragePct": -9}))
        self.assertIn("Abaixo da média", gp.angle({"label": "Bom preço", "deltaAveragePct": -4}))

    def test_hook_does_not_call_store_reference_history(self):
        hook = gp.hook("Produto teste", {"label": "Menor observado", "deltaAveragePct": -5})
        self.assertIn("menor valor observado neste anúncio", hook)
        self.assertNotIn("desconto", hook.lower())
        self.assertNotIn("referência da loja", hook.lower())

    def test_article_destination_wins_when_available(self):
        arts = [{"ids": ["MLB123"], "title": "Guia", "url": "https://example.com/guia"}]
        self.assertEqual(gp.article_for("MLB123", arts)["title"], "Guia")
        self.assertIsNone(gp.article_for("MLB999", arts))

    def test_short_name_limits_length(self):
        self.assertLessEqual(len(gp.short("Produto " * 30)), 72)


if __name__ == "__main__":
    unittest.main()
