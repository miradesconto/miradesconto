import unittest
from datetime import datetime, timezone
from integracoes.automacao.commercial_review import evaluate, WEIGHTS

class CommercialReviewTest(unittest.TestCase):
    def test_gate(self):
        now=datetime.now(timezone.utc)
        p={"id":"MLB1234567","price":100,"available":True,"affiliateUrl":"https://meli.la/abc","imageUrl":"https://example.com/image.jpg"}
        approved={p["id"]:p["affiliateUrl"]}
        evidence={k:{"points":v,"source":"test","date":now.isoformat()} for k,v in WEIGHTS.items()}
        self.assertEqual(evaluate(p,approved,evidence,now)["decision"],"review")
        for k in ("price_verified","image_verified","availability_verified","identity_verified"):
            evidence[k]={"confirmed":True,"source":"test","date":now.isoformat()}
        self.assertEqual(evaluate(p,approved,evidence,now)["decision"],"publish_candidate")
        p["price"]=None
        self.assertEqual(evaluate(p,approved,evidence,now)["decision"],"review")
    def test_missing(self):
        self.assertEqual(evaluate({}, {}, {}, datetime.now(timezone.utc))["score"],0)
