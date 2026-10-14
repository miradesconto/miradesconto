import copy
import sys
import unittest
from unittest.mock import patch
from urllib.request import Request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "integracoes/mercadolivre"))
import discover_candidates as d

SEED = "MLB1234567890"
NEW = "MLB2345678901"
OUTSIDE = "MLB9876543210"
SELLER = 453210987
NOW = datetime(2026, 10, 14, 20, 30, tzinfo=timezone.utc)

SEED_ROW = {"id": SEED, "name": "Notebook Lenovo Ryzen 5", "category": "Notebooks",
            "affiliateUrl": "https://meli.la/Abc123"}
CATALOG = {"products": [SEED_ROW], "publishedIds": [SEED]}
SEARCH_RESULT = {
    "results": [
        {"id": NEW, "title": "Notebook Lenovo Ryzen 5 16GB SSD", "seller": {"id": SELLER},
         "permalink": "https://produto.mercadolivre.com.br/MLB-2345678901-notebook-_JM",
         "status": "active", "price": 100, "original_price": 200},
        {"id": "MLB2345678902", "title": "Brinquedo Infantil Notebook de Plástico",
         "seller": {"id": SELLER},
         "permalink": "https://produto.mercadolivre.com.br/MLB-2345678902-brinquedo-_JM"},
        {"id": OUTSIDE, "title": "Notebook Asus i5", "seller": {"id": 999},
         "permalink": "https://produto.mercadolivre.com.br/MLB-9876543210-notebook-_JM"},
        {"id": SEED, "title": "Notebook Lenovo Ryzen 5", "seller": {"id": SELLER},
         "permalink": "https://produto.mercadolivre.com.br/MLB-1234567890-notebook-_JM"},
    ]
}


class API:
    def __init__(self, *, block=None):
        self.paths = []
        self.block = block

    def get(self, path):
        self.paths.append(path)
        if self.block == "bulk" and path.startswith("/items/bulk?"):
            raise d.AccessError(403)
        if self.block == "seller" and path.startswith("/sites/"):
            raise d.AccessError(403)
        if self.block == "price" and "/sale_price?" in path:
            raise d.AccessError(403)
        if path.startswith("/items/bulk?"):
            return [{"id": SEED, "status_code": 200,
                     "body": {"id": SEED, "seller_id": SELLER}}]
        if path.startswith("/sites/MLB/search?"):
            return copy.deepcopy(SEARCH_RESULT)
        if path == f"/items/{NEW}":
            return {"id": NEW, "seller_id": SELLER, "site_id": "MLB",
                    "status": "active", "currency_id": "BRL", "variations": [],
                    "permalink": SEARCH_RESULT["results"][0]["permalink"]}
        if path == f"/items/{NEW}/sale_price?context=channel_marketplace":
            return {"currency_id": "BRL", "amount": 799.0, "regular_amount": 999.0}
        raise AssertionError(f"Unexpected API path: {path}")


class DiscoveryTests(unittest.TestCase):
    def test_end_to_end_candidates_are_not_published(self):
        client = API()
        report = d.discover(CATALOG, client, now=NOW)
        self.assertEqual(report["newCandidates"], 1)
        self.assertEqual(report["pricesConfirmed"], 1)
        self.assertFalse(report["published"])
        self.assertEqual(report["mode"], "review_only")
        result = report["candidates"][0]
        self.assertEqual(result["id"], NEW)
        self.assertEqual(result["currentPrice"], 799)
        self.assertEqual(result["storeReferencePrice"], 999)
        self.assertGreater(result["storeAdvertisedDiscountPct"], 19)
        self.assertFalse(result["historicalDiscountVerified"])
        self.assertFalse(result["eligibleForPublication"])
        self.assertNotIn("affiliateUrl", result)
        self.assertTrue(any("/items/bulk?" in path for path in client.paths))
        self.assertTrue(any("/sale_price?" in path for path in client.paths))

    def test_access_denied_is_fail_closed(self):
        for blocked, expected in (("bulk", 0), ("seller", 0), ("price", 1)):
            with self.subTest(blocked=blocked):
                report = d.discover(CATALOG, API(block=blocked), now=NOW)
                self.assertEqual(report["newCandidates"], expected)
                self.assertEqual(report["pricesConfirmed"], 0)
                self.assertFalse(report["published"])
                if blocked == "price":
                    self.assertEqual(report["candidates"][0]["priceStatus"], "unverified")
                    self.assertEqual(report["priceAccess"], "blocked_http_403")
                else:
                    self.assertEqual(report["discoveryAccess"], "blocked_http_403")

    def test_no_seller_seeds_reports_no_source(self):
        result = d.discover({"products": [], "publishedIds": []}, API(), now=NOW)
        self.assertEqual(result["discoveryAccess"], "no_sources")
        self.assertEqual(result["candidates"], [])

    def test_bulk_v2_checks_root_body_and_seller(self):
        entries = [
            {"id": SEED, "status_code": 200,
             "body": {"id": OUTSIDE, "seller_id": 77}},
            {"id": SEED, "status_code": 403,
             "body": {"id": SEED, "seller_id": 88}},
            {"id": SEED, "status_code": 200,
             "body": {"id": SEED, "seller_id": SELLER}},
            {"id": OUTSIDE, "status_code": 200,
             "body": {"id": OUTSIDE, "seller_id": 99}},
        ]
        self.assertEqual(d.sellers_from_bulk(entries, [SEED]), [SELLER])

    def test_rejects_wrong_sellers_items_variations_and_links(self):
        self.assertEqual(len(d.candidates_for_seller(SEARCH_RESULT, SELLER, {SEED})), 1)
        for url in (
            "http://produto.mercadolivre.com.br/MLB-2345678901-notebook-_JM",
            "https://example.com/MLB-2345678901-notebook-_JM",
            "https://www.mercadolivre.com.br/p/MLB2345678901",
            "https://produto.mercadolivre.com.br/MLB-2345678901-notebook-_JM?searchVariation=5",
            "https://produto.mercadolivre.com.br/MLB-9876543210-notebook-_JM",
        ):
            with self.subTest(url=url):
                self.assertIsNone(d.canonical_product_link(url, NEW))

    def test_price_reference_not_claimed_as_historical(self):
        row = {"id": NEW}
        value = d.attach_sale_price(row, {
            "currency_id": "BRL", "amount": 100, "regular_amount": 130
        }, NOW.isoformat())
        self.assertTrue(value["storeAdvertisedDiscountPct"] > 0)
        self.assertIs(value["historicalDiscountVerified"], False)
        self.assertIs(value["eligibleForPublication"], False)
        self.assertEqual(d.attach_sale_price(row, {
            "currency_id": "USD", "amount": 100}, NOW.isoformat()), row)
        self.assertEqual(d.attach_sale_price(row, {
            "currency_id": "BRL", "amount": True}, NOW.isoformat()), row)

    def test_explicit_seller_ids_and_no_credentials(self):
        self.assertEqual(d.parse_seller_ids("123, 456"), [123, 456])
        for invalid in ["0", "-1", "1;2", "a", "1,2,3,4,5,6,7"]:
            with self.assertRaises(ValueError):
                d.parse_seller_ids(invalid)
        self.assertEqual(d.choose_sellers(API(), CATALOG, [SELLER]), [SELLER])
        with self.assertRaisesRegex(ValueError, "ACCESS_TOKEN"):
            d.Client("")

    def test_item_identity_status_and_variations_are_required(self):
        item = API().get(f"/items/{NEW}")
        for changes in ({"id": OUTSIDE}, {"seller_id": 999}, {"status": "paused"},
                        {"currency_id": "USD"}, {"site_id": "MLA"},
                        {"variations": None}, {"variations": [{"id": 123}]}):
            with self.subTest(changes=changes):
                client = API()
                original = client.get
                def get(path):
                    return dict(item, **changes) if path == f"/items/{NEW}" else original(path)
                with patch.object(client, "get", side_effect=get) as mocked:
                    report = d.discover(CATALOG, client, now=NOW)
                self.assertEqual(report["pricesConfirmed"], 0)
                self.assertEqual(report["candidates"][0]["priceStatus"], "unverified")
                self.assertFalse(any("sale_price" in call.args[0] for call in mocked.call_args_list))

    def test_no_available_claim_when_search_fails(self):
        for error in (d.AccessError(429), d.AccessError(500), ValueError("bad JSON"),
                      RuntimeError("connection")):
            client = API()
            with patch.object(client, "get", side_effect=error):
                report = d.discover(CATALOG, client, [SELLER], now=NOW)
            self.assertNotEqual(report["discoveryAccess"], "available")
            self.assertEqual(report["sellersExamined"], 0)

    def test_bulk_item_denial_and_transport_failure_are_reported(self):
        client = API()
        with patch.object(client, "get", return_value=[{"id": SEED, "status_code": 403}]):
            report = d.discover(CATALOG, client, now=NOW)
        self.assertEqual(report["discoveryAccess"], "blocked_http_403")
        with patch.object(client, "get", side_effect=RuntimeError("connection")):
            report = d.discover(CATALOG, client, now=NOW)
        self.assertEqual(report["discoveryAccess"], "unverified_error")

    def test_pilot_is_limited_to_five(self):
        client = API()
        rows = [dict(SEARCH_RESULT["results"][0], id=f"MLB23456789{i:02d}",
                     permalink=f"https://produto.mercadolivre.com.br/MLB-23456789{i:02d}-notebook-_JM")
                for i in range(12)]
        with patch.object(client, "get", return_value={"results": rows}) as mocked:
            report = d.discover(CATALOG, client, [SELLER], now=NOW)
        self.assertEqual(report["newCandidates"], 5)
        self.assertEqual(mocked.call_count, 6)  # One search, five item checks.

    def test_bearer_redirects_are_blocked(self):
        client = d.Client("synthetic-test-secret")
        handler = next(h for h in client.opener.handlers if isinstance(h, d.NoRedirect))
        request = Request(d.API + "/items/test", headers={"Authorization": "Bearer synthetic-test-secret"})
        for target in ("https://example.com/", d.API + "/other"):
            self.assertIsNone(handler.redirect_request(request, None, 302, "Found", {}, target))

    def test_output_cannot_overwrite_public_files(self):
        for target in ("dados/catalogo.json", "preview/../links-afiliados.json", "preview/file.txt"):
            with self.subTest(target=target), patch.object(d, "Client") as client:
                with self.assertRaises(ValueError):
                    d.main(["--output", str(d.ROOT / target)])
                client.assert_not_called()

    def test_canonical_link_drops_opaque_tracking(self):
        url = SEARCH_RESULT["results"][0]["permalink"]
        self.assertEqual(d.canonical_product_link(url + "?opaque=secret#tracking=secret", NEW), url)

    def test_echoed_secret_never_reaches_artifact(self):
        with patch.dict(d.os.environ, {"ACCESS_TOKEN": "synthetic-test-secret"}), \
                patch.object(d, "discover", return_value={"title": "synthetic-test-secret"}), \
                patch.object(Path, "write_text") as write:
            with self.assertRaises(ValueError):
                d.main(["--output", str(d.ROOT / "preview/test-secret.json")])
            write.assert_not_called()

if __name__ == "__main__":
    unittest.main()
