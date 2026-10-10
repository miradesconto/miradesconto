"""Destinos reais e falhas de proveniência/rastreio; sem requisições ao ML."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_affiliate_links", ROOT / "integracoes/cloudflare/build_affiliate_links.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
ID = "MLB1234567890"


def fixture():
    p = {"id": ID, "affiliateUrl": "https://meli.la/individual",
         "productUrl": f"https://produto.mercadolivre.com.br/MLB-1234567890-modelo-_JM"}
    a = {"id": ID, "affiliateUrl": p["affiliateUrl"], "productUrl": p["productUrl"],
         "fullAffiliateUrl": "https://www.mercadolivre.com.br/social/cj123?matt_word=instagram&matt_tool=29904275&ref=A%2BB%2FC%3D&forceInApp=true"}
    return {"metadata": {}, "products": [p], "publishedIds": [ID]}, [a]


class AffiliateRegistryTests(unittest.TestCase):
    def test_real_registry_reproducible_and_individual(self):
        catalog = json.loads((ROOT / "dados/catalogo.json").read_text())
        archive = json.loads((ROOT / "links-afiliados.json").read_text())
        registry = builder.build_registry(catalog, archive)
        expected = json.loads((ROOT / "integracoes/cloudflare/affiliate-links.json").read_text())
        self.assertEqual(registry, expected)
        self.assertEqual(set(registry), set(catalog["publishedIds"]))
        self.assertTrue(all(p["kind"] in ("tracked_product", "signed_link") for p in registry.values()))

    def test_signed_url_preserved_without_reserializing(self):
        catalog, archive = fixture()
        parts = builder.build_registry(catalog, archive)[ID]
        self.assertEqual(parts["baseUrl"] + parts["search"] + parts["hash"], archive[0]["fullAffiliateUrl"])
        self.assertIn("A%2BB%2FC%3D", parts["search"])

    def test_generic_list_without_product_tracking_refused(self):
        catalog, archive = fixture()
        catalog["metadata"]["affiliateSources"] = [catalog["products"][0]["affiliateUrl"]]
        with self.assertRaises(ValueError):
            builder.build_registry(catalog, archive)

    def test_missing_or_ambiguous_official_link_refused(self):
        catalog, archive = fixture()
        for values in [[], archive + [copy.deepcopy(archive[0])]]:
            with self.assertRaises(ValueError):
                builder.build_registry(catalog, values)

    def test_wrong_item_variation_or_missing_ref_refused(self):
        for change in ["item", "variation", "ref", "host"]:
            catalog, archive = fixture()
            if change == "item": archive[0]["productUrl"] = archive[0]["productUrl"].replace("1234567890", "9999999999")
            if change == "variation": catalog["products"][0]["variationId"] = "123"
            if change == "ref": archive[0]["fullAffiliateUrl"] = archive[0]["fullAffiliateUrl"].replace("ref=A%2BB%2FC%3D&", "")
            if change == "host": archive[0]["fullAffiliateUrl"] = archive[0]["fullAffiliateUrl"].replace("www.mercadolivre.com.br", "evil.test")
            with self.assertRaises(ValueError, msg=change):
                builder.build_registry(catalog, archive)

    def test_previous_campaign_does_not_replace_current_link(self):
        catalog, archive = fixture()
        old = {**archive[0], "affiliateUrl": "https://meli.la/old-campaign", "fullAffiliateUrl": "https://evil.test/"}
        self.assertEqual(builder.build_registry(catalog, archive), builder.build_registry(catalog, [old, *archive]))

    def test_observed_variation_does_not_rewrite_unbound_official_link(self):
        catalog, archive = fixture()
        catalog['products'][0]['priceCheck'] = {'variationId': '190223671249'}
        destination = builder.build_registry(catalog, archive)[ID]
        self.assertIsNone(destination['variationId'])
        self.assertEqual(destination['baseUrl']+destination['search']+destination['hash'],archive[0]['fullAffiliateUrl'])

    def test_another_affiliate_account_refused(self):
        catalog, archive = fixture()
        archive[0]["fullAffiliateUrl"] = archive[0]["fullAffiliateUrl"].replace("matt_tool=29904275", "matt_tool=12345678")
        with self.assertRaises(ValueError):
            builder.build_registry(catalog, archive)


if __name__ == "__main__":
    unittest.main()
