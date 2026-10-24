import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "integracoes/pinterest"))
import fila_automatica as queue


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "assets/pinterest").mkdir(parents=True)
        (self.root / "_artigos").mkdir()
        data = b"approved-image-fixture"
        (self.root / "assets/pinterest/final.png").write_bytes(data)
        self.post = {
            "key": "produto", "slug": "produto", "title": "Produto: o que conferir",
            "affiliate": "https://meli.la/abcDEF",
            "image": "assets/pinterest/final.png",
            "sha256": hashlib.sha256(data).hexdigest(),
            "link": "https://miradesconto.com.br/blog/produto/",
            "approved": True
        }
        (self.root / "_artigos/produto.md").write_text(
            "---\npublished: true\n---\nhttps://meli.la/abcDEF", encoding="utf-8")
        self.config = {"schemaVersion": 1,
                       "boardName": "Ofertas de Tecnologia e Achadinhos | MiraDesconto",
                       "posts": [self.post]}
        self.state = {"schemaVersion": 1, "posts": {}}
        self.saved = []

    def run_queue(self, **kwargs):
        return queue.run(self.config, self.state, "token", publish=True,
                         root=self.root, save=kwargs.pop("save", lambda s: self.saved.append(copy.deepcopy(s))),
                         check_live=kwargs.pop("check_live", lambda p: None), **kwargs)

    def test_draft_has_no_network(self):
        with patch.object(queue, "pinterest_request") as api:
            queue.run(self.config, self.state, "", root=self.root)
            api.assert_not_called()

    def test_rejects_changed_art_before_network(self):
        self.post["sha256"] = "0" * 64
        with patch.object(queue, "pinterest_request") as api:
            with self.assertRaises(ValueError):
                self.run_queue()
            api.assert_not_called()

    def test_rejects_wrong_affiliate_in_article(self):
        self.post["affiliate"] = "https://meli.la/otherLink"
        with self.assertRaises(ValueError):
            queue.validate(self.post, self.root)

    def test_dedupe_site_tracking_and_direct_affiliate(self):
        for existing in [self.post["link"] + "?utm_source=pinterest", self.post["affiliate"]]:
            self.state = {"schemaVersion": 1, "posts": {}}
            with patch.object(queue, "find_board", return_value="123456"), patch.object(
                    queue, "pinterest_request", return_value={
                        "items": [{"id": "99", "link": existing}]} ) as api:
                self.run_queue()
                self.assertEqual(api.call_count, 1)
                self.assertEqual(self.state["posts"]["produto"]["pinId"], "99")

    def test_checkpoint_precedes_post_and_success_is_verified(self):
        def api(token, path, payload=None):
            if path.startswith("/pins?"):
                return {"items": []}
            if path == "/pins":
                self.assertEqual(self.saved[-1]["posts"]["produto"]["status"], "uncertain")
                return {"id": "999"}
            return {"link": self.post["link"], "board_id": "123456"}
        with patch.object(queue, "find_board", return_value="123456"), patch.object(
                queue, "pinterest_request", side_effect=api):
            self.run_queue()
        self.assertEqual(self.saved[-1]["posts"]["produto"]["status"], "published")

    def test_failed_remote_checkpoint_prevents_post(self):
        with patch.object(queue, "find_board", return_value="123456"), patch.object(
                queue, "pinterest_request", return_value={"items": []}) as api:
            with self.assertRaises(OSError):
                self.run_queue(save=lambda s: (_ for _ in ()).throw(OSError("push failed")))
            self.assertEqual(api.call_count, 1)

    def test_uncertain_response_blocks_next_run(self):
        with patch.object(queue, "find_board", return_value="123456"), patch.object(
                queue, "pinterest_request", side_effect=[{"items": []}, {}]):
            with self.assertRaises(RuntimeError):
                self.run_queue()
        with patch.object(queue, "pinterest_request") as api:
            with self.assertRaises(RuntimeError):
                self.run_queue()
            api.assert_not_called()

    def test_unavailable_live_page_prevents_post(self):
        with patch.object(queue, "find_board", return_value="123456"), patch.object(
                queue, "pinterest_request", return_value={"items": []}) as api:
            with self.assertRaises(RuntimeError):
                self.run_queue(check_live=lambda p: (_ for _ in ()).throw(RuntimeError("offline")))
            self.assertEqual(api.call_count, 1)
            self.assertEqual(self.saved, [])

    def test_normalization_preserves_affiliate_parameters(self):
        self.assertNotEqual(queue.normalize("https://www.mercadolivre.com.br/p/x?matt_tool=1"),
                            queue.normalize("https://www.mercadolivre.com.br/p/x?matt_tool=2"))


if __name__ == "__main__":
    unittest.main()
