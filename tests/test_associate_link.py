import copy
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'integracoes/mercadolivre'))
import associate_link

FIRST = "MLB1234567890"
SECOND = "MLB9876543210"
SOURCE = "https://produto.mercadolivre.com.br/MLB-1234567890-monitor-_JM"
NEW_LINK = "https://meli.la/novo123"


class FakeResponse:
    def __init__(self, url):
        self.url = url
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def geturl(self):
        return self.url


class FakeOpener:
    def __init__(self, url):
        self.url = url
    def open(self, request, timeout=None):
        return FakeResponse(self.url)


class AssociateLinkTests(unittest.TestCase):
    def setUp(self):
        self.old = "https://meli.la/antigo123"
        self.catalog = {
            "products": [
                {"id": FIRST, "name": "Monitor", "productUrl": SOURCE,
                 "affiliateUrl": self.old, "rank": 1, "featured": True,
                 "priceCheck": {"status": "verified"}},
                {"id": SECOND, "name": "Mouse", "productUrl":
                 "https://produto.mercadolivre.com.br/MLB-9876543210-mouse-_JM",
                 "affiliateUrl": "https://meli.la/outro456",
                 "rank": 2, "featured": True}
            ],
            "publishedIds": [FIRST, SECOND],
        }
        self.archive = [
            {"id": FIRST, "affiliateUrl": self.old, "fullAffiliateUrl": "https://www.mercadolivre.com.br/social/old"},
            {"id": SECOND, "affiliateUrl": "https://meli.la/outro456"},
        ]
        self.when = datetime(2026, 10, 14, tzinfo=timezone.utc)

    def change(self, link=NEW_LINK, destination=(FIRST, None), catalog=None, archive=None):
        return associate_link.prepare(
            catalog if catalog is not None else self.catalog,
            archive if archive is not None else self.archive,
            FIRST, link, destination, self.when
        )

    def test_safe_review_stages_link_without_mutating_source(self):
        before_catalog, before_archive = copy.deepcopy(self.catalog), copy.deepcopy(self.archive)
        new, records, changed = self.change()
        self.assertTrue(changed)
        self.assertEqual(before_catalog, self.catalog)
        self.assertEqual(before_archive, self.archive)
        self.assertEqual(new["publishedIds"], [SECOND])
        self.assertEqual(new["products"][0]["affiliateUrl"], NEW_LINK)
        self.assertNotIn("priceCheck", new["products"][0])
        self.assertFalse(new["products"][0]["featured"])
        self.assertEqual(new["products"][1], self.catalog["products"][1] |
                         {"rank": 1, "featured": True})
        self.assertEqual(records[0]["affiliateUrl"], NEW_LINK)
        self.assertEqual(records[0]["previousAffiliateUrl"], self.old)
        self.assertNotIn("fullAffiliateUrl", records[0])

    def test_refuses_wrong_item_or_existing_other_link(self):
        with self.assertRaisesRegex(ValueError, "outro anúncio"):
            self.change(destination=(SECOND, None))
        with self.assertRaisesRegex(ValueError, "outro produto"):
            self.change(link="https://meli.la/outro456")

    def test_refuses_other_variation_and_unconfirmed_catalogue_identity(self):
        with self.assertRaisesRegex(ValueError, "mesma variação"):
            self.change(destination=(FIRST, "1234"))
        bad = copy.deepcopy(self.catalog)
        bad["products"][0]["productUrl"] = "https://www.mercadolivre.com.br/social/foo"
        with self.assertRaisesRegex(ValueError, "identidade verificável"):
            self.change(catalog=bad)

    def test_rejects_untracked_original_and_is_idempotent(self):
        bad = copy.deepcopy(self.catalog)
        bad["products"][0]["affiliateUrl"] = "https://meli.la/estranho"
        with self.assertRaisesRegex(ValueError, "procedência"):
            self.change(catalog=bad)
        original, rows, changed = self.change(link=self.old)
        self.assertFalse(changed)
        self.assertEqual(original, self.catalog)
        self.assertEqual(rows, self.archive)

    def test_accepts_exact_direct_destination(self):
        self.assertEqual(
            associate_link.direct_destination(
                NEW_LINK, opener=FakeOpener(
                    "https://produto.mercadolivre.com.br/MLB-1234567890-monitor-_JM"
                )
            ), (FIRST, None)
        )
        for destination in (
            "https://www.mercadolivre.com.br/social/foo?wid=MLB1234567890",
            "https://www.mercadolivre.com.br/lists/bar?wid=MLB1234567890",
            "https://www.mercadolivre.com.br/help?wid=MLB1234567890",
            "https://example.com/MLB-1234567890-produto",
        ):
            with self.subTest(destination=destination):
                with self.assertRaises(ValueError):
                    associate_link.direct_destination(NEW_LINK, opener=FakeOpener(destination))


if __name__ == "__main__":
    unittest.main()
