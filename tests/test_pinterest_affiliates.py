import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "integracoes/pinterest"))
import fila_afiliados as affiliate


class AffiliateQueueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        folder = self.root / "assets/pinterest"
        folder.mkdir(parents=True)
        img = b"an-approved-image"
        (folder / "one.png").write_bytes(img)
        self.post = {"key": "one", "merchant": "mercado_livre",
                     "affiliate": "https://meli.la/1DCVFvT",
                     "link": "https://meli.la/1DCVFvT",
                     "title": "Produto em destaque",
                     "description": "Veja informações e condições no anúncio do produto",
                     "image": "assets/pinterest/one.png",
                     "sha256": hashlib.sha256(img).hexdigest(),
                     "confirmed_channel": True, "approved": True}
        self.queue = {"schemaVersion": 1, "boardName":
                      "Ofertas de Tecnologia e Achadinhos | MiraDesconto",
                      "posts": [self.post]}
        self.state = {"schemaVersion": 1, "posts": {}}

    def test_direct_link(self):
        image, description = affiliate.validate(self.post, self.root)
        self.assertTrue(image.exists())
        self.assertIn("comissão", description)

    def test_site_link_rejected(self):
        self.post["link"] = "https://miradesconto.com.br/blog/post/"
        with self.assertRaises(ValueError):
            affiliate.validate(self.post, self.root)

    def test_shopee_allowed_only_official_host(self):
        self.post["merchant"] = "shopee"
        self.post["affiliate"] = self.post["link"] = "https://s.shopee.com.br/abcdef"
        affiliate.validate(self.post, self.root)
        self.post["affiliate"] = "https://fake-shopee.example/abcdef"
        with self.assertRaises(ValueError):
            affiliate.validate(self.post, self.root)

    def test_approval_required(self):
        self.post["confirmed_channel"] = False
        with self.assertRaises(ValueError):
            affiliate.validate(self.post, self.root)

    def test_checkpoint_before_post_and_verified_destination(self):
        saved = []
        def api(token, path, payload=None):
            if path.startswith("/pins?"):
                return {"items": []}
            if path == "/pins":
                self.assertEqual(payload["link"], self.post["affiliate"])
                self.assertEqual(saved[-1]["posts"]["one"]["status"], "uncertain")
                return {"id": "123456"}
            return {"link": self.post["affiliate"], "board_id": "123"}
        with patch.object(affiliate, "find_board", return_value="123"), patch.object(
                affiliate, "pinterest_request", side_effect=api):
            affiliate.run(self.queue, self.state, "token", publish=True, root=self.root,
                          save=lambda x: saved.append(json.loads(json.dumps(x))))
        self.assertEqual(saved[-1]["posts"]["one"]["status"], "published")


if __name__ == "__main__":
    unittest.main()
