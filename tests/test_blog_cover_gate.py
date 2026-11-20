"""Regressões para a trava de capa editorial."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SRC = Path(__file__).resolve().parents[1] / "integracoes/automacao/check_blog_covers.py"
spec = importlib.util.spec_from_file_location("check_blog_covers", SRC)
covers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(covers)


class BlogCoverGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "assets/blog").mkdir(parents=True)
        (self.root / "_artigos").mkdir()
        self.patch_root = patch.object(covers, "ROOT", self.root)
        self.patch_root.start()
        self.addCleanup(self.patch_root.stop)
        self.good_svg = self.root / "assets/blog/cover.svg"
        self.good_svg.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900">'
            + '<path d="M1 1h10v10z"/>' * 25 + '</svg>', encoding="utf-8")

    def article(self, image='', status='publicado'):
        field = 'custom_image: "' + image + '"\n' if image else ''
        f = self.root / "_artigos/new.md"
        f.write_text('---\nstatus: "' + status + '"\npublished: true\n'
                     + field + '---\n# Teste\n', encoding="utf-8")
        return f

    def test_reprova_publicado_sem_capa(self):
        with self.assertRaisesRegex(ValueError, 'Capa ausente'):
            covers.validate_one(self.article())

    def test_reprova_caminho_quebrado(self):
        with self.assertRaisesRegex(ValueError, 'não encontrada'):
            covers.validate_one(self.article('/assets/blog/missing.png'))

    def test_reprova_placeholder_externo(self):
        with self.assertRaisesRegex(ValueError, 'local'):
            covers.validate_one(self.article('https://example.com/thumb.png'))

    def test_aprova_arte_local_real(self):
        self.assertEqual(covers.validate_one(self.article('/assets/blog/cover.svg')),
                         '/assets/blog/cover.svg')

    def test_rascunho_pode_aguardar_capa(self):
        self.assertIn('rascunho', covers.validate_one(self.article(status='rascunho')))


if __name__ == '__main__':
    unittest.main()
