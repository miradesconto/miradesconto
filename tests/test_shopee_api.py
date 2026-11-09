import json
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from integracoes.shopee.afiliados import ApiError, collect, feed_product, price_snapshot, report_page, tokens


class ShopeeApiTests(TestCase):
    def test_missing_offer_and_keyword_failure_preserve_other_results(self):
        product = {
            "shopId": 10, "itemId": 20, "productName": "Mouse Attack Shark X11",
            "priceMin": "120", "priceMax": "132.99", "productCatIds": [111],
        }

        class API:
            def products(self, **filters):
                if "keyword" in filters:
                    raise ApiError("10000 (erro de sistema)")
                if filters.get("itemId") == 21:
                    return []
                return [product]

            def call(self, operation, fields, **filters):
                return {"nodes": [{"netCommission": "8.00"}]} if operation == "conversionReport" else {}

        args = SimpleNamespace(keyword="Attack Shark X11", generate_links=False, validation_id=None)
        with patch("integracoes.shopee.afiliados.catalog_rows", return_value=[(10, 20, ""), (10, 21, "")]):
            snapshot, private = collect(API(), args)
        self.assertEqual(snapshot["discovery"]["keyword_source"], "filtro_local")
        self.assertEqual(len(snapshot["discovery"]["keyword_results"]), 1)
        self.assertEqual(snapshot["checks"]["catalogo/21"]["status"], "falhou")
        self.assertEqual(snapshot["checks"]["validatedReport"]["status"], "bloqueado")
        self.assertEqual(price_snapshot(snapshot), {
            "20": {"min": "120.00", "max": "132.99", "checked_at": snapshot["checked_at"]},
        })
        self.assertEqual(private["conversions"]["net_commission_brl"], "8.00")
        self.assertNotIn("net_commission_brl", str(snapshot))

    def test_report_refuses_to_label_an_incomplete_total_as_complete(self):
        class API:
            def call(self, operation, fields, **filters):
                return {"nodes": [{"netCommission": "2.50"}],
                        "pageInfo": {"hasNextPage": True, "scrollId": "same"}}

        result = report_page(API(), "conversionReport")
        self.assertFalse(result["complete"])
        self.assertIsNone(result["net_commission_brl"])


    def test_feed_checks_title_and_listing_identity(self):
        row = {"title": "Mouse Gamer Sem Fio", "itemid": "123",
               "product_link": "https://shopee.com.br/Mouse-Gamer-i.456.123?tracking=secret"}
        parsed = feed_product({"columns": json.dumps(row)}, tokens("mouse gamer"))
        self.assertEqual(parsed["product_url"], "https://shopee.com.br/product/456/123")
        self.assertIsNone(feed_product({"columns": row}, tokens("teclado")))
        row["itemid"] = "999"
        self.assertIsNone(feed_product({"columns": row}, tokens("mouse")))
