"""Testes locais sem chamadas reais à API do Pinterest."""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'integracoes' / 'pinterest'))

import publicar
from link_rules import affiliate_description, validate_ml_link


class PinterestHybridTests(unittest.TestCase):
    IMAGE = 'https://miradesconto.com.br/assets/pinterest/arte-propria.jpg'
    BOARD = '123456789012345'
    OFFER = 'https://meli.la/1zsVjAj'
    TITLE = 'Notebook Acer Aspire Go i7'
    CAPTION = 'Confira as especificações e a garantia antes de comprar este notebook'

    def test_site_mode_preserves_existing_workflow(self):
        title, link, description = publicar.validate_publication(
            'site', 'iphone-15-ou-16-em-promocao', '', '', '',
            self.BOARD, self.IMAGE, 'PUBLICAR')
        self.assertIn('iPhone', title)
        self.assertEqual(link, 'https://miradesconto.com.br/blog/iphone-15-ou-16-em-promocao/')
        self.assertIn('comissão', description)

    def test_affiliate_mode_uses_direct_destination_and_disclosure(self):
        title, link, description = publicar.validate_publication(
            'mercado_livre', '', self.OFFER, self.TITLE, self.CAPTION,
            self.BOARD, self.IMAGE, 'PUBLICAR')
        self.assertEqual((title, link), (self.TITLE, self.OFFER))
        self.assertIn('Conteúdo com link de afiliado', description)
        self.assertIn('podemos receber comissão', description)

    def test_confirmation_and_owned_art_required(self):
        with self.assertRaisesRegex(ValueError, 'PUBLICAR'):
            publicar.validate_publication(
                'mercado_livre', '', self.OFFER, self.TITLE, self.CAPTION,
                self.BOARD, self.IMAGE, '')
        with self.assertRaisesRegex(ValueError, 'Arte final'):
            publicar.validate_publication(
                'mercado_livre', '', self.OFFER, self.TITLE, self.CAPTION,
                self.BOARD, 'https://evil.test/art.png', 'PUBLICAR')

    def test_no_mixed_destinations(self):
        with self.assertRaises(ValueError):
            publicar.validate_publication(
                'mercado_livre', 'um-artigo', self.OFFER, self.TITLE, self.CAPTION,
                self.BOARD, self.IMAGE, 'PUBLICAR')
        with self.assertRaises(ValueError):
            publicar.validate_publication(
                'site', 'iphone-15-ou-16-em-promocao', self.OFFER, '', '',
                self.BOARD, self.IMAGE, 'PUBLICAR')

    def test_affiliate_link_allowlist_rejects_lookalikes(self):
        self.assertEqual(validate_ml_link(self.OFFER), self.OFFER)
        for link in (
            'http://meli.la/1zsVjAj', 'https://meli.la.evil.test/x',
            'https://evil.test/go/mercadolivre', 'https://meli.la@evil.test/path',
            'https://meli.la/1zsVjAj?next=evil', 'https://meli.la/1zsVjAj#frag',
            'https://meli.la/1zsVjAj\n',
        ):
            with self.subTest(link=link), self.assertRaises(ValueError):
                validate_ml_link(link)

    def test_bad_destination_and_caption_fail(self):
        with self.assertRaisesRegex(ValueError, 'Destino inválido'):
            publicar.validate_publication(
                'externo', '', self.OFFER, self.TITLE, self.CAPTION,
                self.BOARD, self.IMAGE, 'PUBLICAR')
        with self.assertRaises(ValueError):
            affiliate_description('Compre agora')


if __name__ == '__main__':
    unittest.main()
