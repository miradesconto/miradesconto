"""Unit tests offline for safe image snapshotting and API fallback."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

# O pipeline geral do catálogo não instala requests. O workflow do minerador
# instala a dependência e executa estes testes de forma completa.
try:
    import requests
except ModuleNotFoundError as exc:
    raise unittest.SkipTest("requests instalado e validado no workflow do minerador") from exc

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "integracoes/automacao/cache_imagens_ofertas.py"
spec = importlib.util.spec_from_file_location("cache_image_test", SCRIPT)
cache = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cache)


class FakeResponse:
    def __init__(self, content, url):
        self.content = content
        self.url = url
        self.headers = {"Content-Type": "image/jpeg"}
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def raise_for_status(self):
        pass
    def iter_content(self, chunk_size):
        yield self.content


class CacheOffersTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "api").mkdir()
        self.jpeg = b"\xff\xd8\xff\xe0" + b"\x11" * 700
        self.item = {
            "titulo": "Mouse Gamer RGB",
            "preco_atual": 34.90,
            "imagem": "https://cf.shopee.com.br/file/sg-11134201-823ob-mp7wv1fcnx8rc4",
            "link_afiliado": "https://s.shopee.com.br/123",
            "loja": "Shopee"
        }

    def tearDown(self):
        self.tmp.cleanup()

    def request(self, url, **kwargs):
        return FakeResponse(self.jpeg, url)

    def test_official_cdn_mirroring(self):
        img = cache.cached_image(self.item, self.root, getter=self.request)
        self.assertRegex(img, r"^/assets/ofertas/[a-f0-9]{24}\.jpg$")
        self.assertEqual((self.root / img[1:]).read_bytes(), self.jpeg)
        self.assertEqual(self.item["link_afiliado"], "https://s.shopee.com.br/123")

    def test_reuse_existing_photo_on_cdn_error(self):
        img = cache.cached_image(self.item, self.root, getter=self.request)
        def failed(url, **kwargs):
            raise cache.requests.Timeout()
        self.assertEqual(cache.cached_image(self.item, self.root, getter=failed), img)

    def test_no_fake_photo_when_all_hosts_fail(self):
        def failed(url, **kwargs):
            raise cache.requests.Timeout()
        self.assertIsNone(cache.cached_image(self.item, self.root, getter=failed))

    def test_prevent_unknown_host(self):
        self.assertEqual(cache.alternatives("https://example.invalid/image.png"), [])
        self.assertEqual(cache.alternatives("http://cf.shopee.com.br/file/x"), [])

    def test_mirror_writes_feed_and_jekyll_fallback(self):
        items = [{**self.item, "link_afiliado": "https://s.shopee.com.br/" + str(i)} for i in range(5)]
        (self.root / "api/produtos.json").write_text(json.dumps(items), encoding="utf-8")
        result = cache.mirror(self.root, getter=self.request, workers=2)
        self.assertEqual(result["total"], 5)
        self.assertEqual(result["shopee"], 5)
        updated = json.loads((self.root / "api/produtos.json").read_text())
        fallback = json.loads((self.root / "_data/ofertas_automaticas.json").read_text())
        self.assertEqual(updated, fallback)
        self.assertTrue(all(row["imagem"].startswith("/assets/ofertas/") for row in updated))
        self.assertTrue(all((self.root / row["imagem"][1:]).exists() for row in updated))

    def test_curated_shopee_uses_local_photo_without_replacing_affiliate_link(self):
        source = self.root / "_data/shopee_gamer_publicados.json"
        source.parent.mkdir(exist_ok=True)
        data = [{
            "item_id": "58212667892",
            "title": "Monitor Gamer 144Hz",
            "image_url": self.item["imagem"],
            "affiliate_url": "https://s.shopee.com.br/curated123"
        }]
        source.write_text(json.dumps(data), encoding="utf-8")
        photos = cache.mirror_curated_shopee(self.root, getter=self.request)
        self.assertIn("58212667892", photos)
        image = photos["58212667892"]
        self.assertTrue(image.startswith("/assets/ofertas/"))
        self.assertTrue((self.root / image.lstrip("/")).is_file())
        persisted = json.loads((self.root / "_data/shopee_fotos_locais.json").read_text())
        self.assertEqual(persisted, photos)
        self.assertEqual(data[0]["affiliate_url"], "https://s.shopee.com.br/curated123")

    def test_under_four_valid_images_does_not_write_feed(self):
        items = [dict(self.item)]
        p = self.root / "api/produtos.json"
        content = json.dumps(items)
        p.write_text(content, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Apenas 1 fotos válidas"):
            cache.mirror(self.root, getter=self.request)
        self.assertEqual(p.read_text(), content)
        self.assertFalse((self.root / "_data/ofertas_automaticas.json").exists())


if __name__ == "__main__":
    unittest.main()
