"""Testes offline do bot de grupos, sem enviar mensagens."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "grupos_ofertas", ROOT / "integracoes/social/grupos_ofertas.py")
bot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bot)

T = datetime(2026, 11, 12, 16, tzinfo=timezone.utc)


def row(shop="Shopee", link="https://s.shopee.com.br/ABCDE12", price=99.90,
        title="Mouse gamer sem fio com conexão USB para PC"):
    return {"titulo": title, "preco_atual": price, "link_afiliado": link, "loja": shop}


class OfferBotTests(unittest.TestCase):
    def test_valid_links_and_no_nonaffiliate(self):
        self.assertTrue(bot.valid_link("https://s.shopee.com.br/AbC123", "Shopee"))
        self.assertTrue(bot.valid_link("https://meli.la/AbC123", "Mercado Livre"))
        self.assertFalse(bot.valid_link("https://meli.la/1NguveN", "Mercado Livre"))
        self.assertFalse(bot.valid_link("http://meli.la/abc", "Mercado Livre"))
        self.assertFalse(bot.valid_link("https://meli.la.evil.net/x", "Mercado Livre"))
        self.assertFalse(bot.valid_link("https://evil.com/x", "Shopee"))
        self.assertFalse(bot.valid_link("https://www.mercadolivre.com.br/produto/p/123", "Mercado Livre"))
        self.assertFalse(bot.valid_link("https://s.shopee.com.br/abc?redirect=evil", "Shopee"))

    def test_normalize_rejects_bad_or_fake_item(self):
        self.assertIsNotNone(bot.normalize(row()))
        self.assertIsNone(bot.normalize(row(title="Mini Jesus religioso para monitor computador")))
        self.assertIsNone(bot.normalize(row(price=0)))
        self.assertIsNone(bot.normalize(row(price=float("nan"))))
        self.assertIsNone(bot.normalize(row(price=True)))
        self.assertIsNone(bot.normalize(row(title="Não é eletrônico")))

    def test_pick_repeats_and_daily_cap(self):
        one = row()
        p = bot.normalize(one)
        self.assertEqual(bot.select_offer([one], {"events": []}, T, T), p)
        used = [{"id": p["id"], "reservation": "abc", "shop": "Shopee",
                 "at": T.isoformat(), "status": "reserved"}]
        self.assertIsNone(bot.select_offer([one], {"events": used}, T, T))
        self.assertIsNone(bot.select_offer([one], {"events": used * 3}, T, T))
        self.assertEqual(bot.select_offer([one], {"events": [
            {**used[0], "at": (T - timedelta(days=6)).isoformat()}
        ]}, T, T), p)

    def test_reject_stale_feed_and_future_feed(self):
        with self.assertRaises(bot.BotError):
            bot.select_offer([row()], {"events": []}, T, T - timedelta(hours=37))
        with self.assertRaises(bot.BotError):
            bot.select_offer([row()], {"events": []}, T, T + timedelta(minutes=1))

    def test_offer_no_unverified_price_or_deceptive_claim(self):
        item = bot.normalize(row(title="Monitor gamer <240Hz> & monitor 27 polegadas"))
        telegram, whatsapp = bot.build_text(item)
        self.assertIn("&lt;240Hz&gt;", telegram)
        self.assertIn("&amp;", telegram)
        self.assertNotIn("R$ 99,90", telegram)
        self.assertNotIn("menor preço", whatsapp.casefold())
        self.assertIn("comissão", telegram)
        self.assertIn(item["link"], whatsapp)
        prepared = bot.build_reservation(item, T)
        self.assertTrue(prepared["whatsapp_share"].startswith("https://wa.me/?text="))

    def test_reserve_and_finalize_without_network(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            feed = base / "produtos.json"
            state = base / "estado.json"
            prepared = base / "prepared.json"
            receipt = base / "receipt.json"
            feed.write_text(json.dumps([row()]), encoding="utf-8")
            with patch.object(bot, "FEED", feed), patch.object(bot, "STATE", state), \
                 patch.object(bot, "feed_updated_at", return_value=T), \
                 patch.object(bot, "now_utc", return_value=T):
                bot.prepare(prepared)
                self.assertTrue(json.loads(prepared.read_text())["ready"])
                self.assertEqual(bot.read_state(state)["events"][0]["status"], "reserved")
                receipt.write_text(json.dumps({
                    "reservation": json.loads(prepared.read_text())["id"],
                    "status": "sent", "message_id": 56}), encoding="utf-8")
                bot.finish(receipt, prepared)
                self.assertEqual(bot.read_state(state)["events"][0]["status"], "sent")
                self.assertEqual(bot.read_state(state)["events"][0]["message_id"], 56)
                bot.prepare(base / "prepared2.json")
                self.assertFalse(json.loads((base / "prepared2.json").read_text())["ready"])

    def test_send_failure_records_uncertain_without_retry(self):
        with tempfile.TemporaryDirectory() as td:
            file = Path(td) / "prepared.json"
            receipt = Path(td) / "receipt.json"
            entry = bot.build_reservation(bot.normalize(row()), T)
            file.write_text(json.dumps(entry), encoding="utf-8")
            with patch.object(bot, "config_bot", return_value=("12345:ABCDEFGHIJKLMNOPQRSTUVWXYZ", "@MiraDesconto")), \
                 patch.object(bot, "http_json", side_effect=bot.BotError("timeout")) as fake:
                with self.assertRaises(bot.BotError):
                    bot.send(file, receipt)
                self.assertEqual(fake.call_count, 1)
                self.assertEqual(json.loads(receipt.read_text())["status"], "uncertain")


if __name__ == "__main__":
    unittest.main()
