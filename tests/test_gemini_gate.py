import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import urllib.error

spec = importlib.util.spec_from_file_location("gemini_gate", Path(__file__).resolve().parents[1] / ".github/scripts/gemini_gate.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
HEAD, BASE = "a" * 40, "b" * 40
DIFF = "diff --git a/precos.js b/precos.js\n--- a/precos.js\n+++ b/precos.js\n@@ -0,0 +1 @@\n+const preco = 12345;\n"


def finding(severity="CRÍTICO"):
    return {"severity": severity, "category": "PREÇO", "file": "precos.js", "line": 1,
            "evidence": "const preco = 12345;", "reason": "Preço publicado sem fonte verificada."}


class FakeAPI:
    def __init__(self, writable=True, stale=False):
        self.allowed, self.stale, self.reads = writable, stale, 0
        self.writes = []

    def writable(self, login):
        return self.allowed

    def call(self, path, payload=None, method=None):
        if payload is not None:
            self.writes.append((path, payload, method))
            return {"id": 1}
        self.reads += 1
        return {"number": 19, "state": "open", "draft": True,
                "head": {"sha": "c" * 40 if self.stale and self.reads > 1 else HEAD},
                "base": {"sha": BASE, "ref": "main"}}


def event(body=None):
    if body is None:
        return {"pull_request": {"number": 19}}
    return {"issue": {"number": 19, "pull_request": {}},
            "comment": {"body": body, "user": {"login": "maintainer"},
                        "html_url": "https://github.com/o/r/pull/19#issuecomment-123"}}


class ParsingTests(unittest.TestCase):
    def test_clean_approval(self):
        self.assertEqual(gate.parse_review('{"decision":"APROVAR","findings":[]}', {"precos.js"}, DIFF)["decision"], "APROVAR")

    def test_verified_blocker(self):
        gate.parse_review(json.dumps({"decision": "BLOQUEAR", "findings": [finding()]}), {"precos.js"}, DIFF)

    def test_important_does_not_block(self):
        gate.parse_review(json.dumps({"decision": "APROVAR", "findings": [finding("IMPORTANTE")]}), {"precos.js"}, DIFF)

    def test_bad_decisions_never_pass(self):
        invalid = ["", "GATE: BLOQUEAR\nGATE: APROVAR", "```json\n{}\n```",
                   '{"decision":"BLOQUEAR","decision":"APROVAR","findings":[]}',
                   json.dumps({"decision": "BLOQUEAR", "findings": []}),
                   json.dumps({"decision": "APROVAR", "findings": [finding()]}),
                   json.dumps({"decision": "BLOQUEAR", "findings": [finding("IMPORTANTE")]})]
        for raw in invalid:
            with self.subTest(raw=raw), self.assertRaises(gate.NotReviewed):
                gate.parse_review(raw, {"precos.js"}, DIFF)

    def test_false_evidence_category_and_location(self):
        for key, value in [("file", "not-changed.js"), ("category", "ESTILO"), ("line", True),
                           ("evidence", "invented evidence"), ("reason", "")]:
            f = finding(); f[key] = value
            with self.subTest(key=key), self.assertRaises(gate.NotReviewed):
                gate.parse_review(json.dumps({"decision": "BLOQUEAR", "findings": [f]}), {"precos.js"}, DIFF)

    def test_evidence_from_wrong_file_line_or_context(self):
        for key, value in [("file", "other.js"), ("line", 20)]:
            f = finding(); f[key] = value
            with self.assertRaises(gate.NotReviewed):
                gate.parse_review(json.dumps({"decision": "BLOQUEAR", "findings": [f]}), {"precos.js", "other.js"}, DIFF)
        self.assertFalse(gate.evidence_matches(finding(), DIFF.replace("+const", " const")))

    def test_deleted_line_can_be_anchored(self):
        diff = DIFF.replace("@@ -0,0 +1 @@", "@@ -1 +0,0 @@").replace("+const", "-const")
        self.assertTrue(gate.evidence_matches(finding(), diff))

    def test_secret_missing(self):
        with self.assertRaises(gate.NotReviewed):
            gate.gemini_review(DIFF, {"precos.js"}, "", "", "model")

    def test_api_retry_and_redacted_error(self):
        error = urllib.error.HTTPError("https://example", 429, "secret value", {}, None)
        with patch.object(gate, "request_json", side_effect=error) as req, patch.object(gate.time, "sleep"):
            with self.assertRaises(gate.NotReviewed) as result:
                gate.gemini_review(DIFF, {"precos.js"}, "", "key", "model")
            self.assertEqual(req.call_count, 3)
            self.assertNotIn("secret value", str(result.exception))

    def test_truncated_response(self):
        with patch.object(gate, "request_json", return_value={"candidates": [{"finishReason": "MAX_TOKENS"}]}):
            with self.assertRaises(gate.NotReviewed):
                gate.gemini_review(DIFF, {"precos.js"}, "", "key", "model")


class RecoveryTests(unittest.TestCase):
    def review(self, api, response=None, error=None):
        with patch.object(gate, "collect_diff", return_value=(DIFF, {"precos.js"})), \
             patch.object(gate, "gemini_review", return_value=response, side_effect=error), \
             patch.object(gate.Path, "read_text", return_value="trusted policy"):
            return gate.run(event(), "pull_request_target", api, "key", "model")

    def test_block_then_fixed_in_draft(self):
        api = FakeAPI()
        self.assertEqual(self.review(api, {"decision": "BLOQUEAR", "findings": [finding()]}), 1)
        self.assertEqual(self.review(api, {"decision": "APROVAR", "findings": []}), 0)
        self.assertTrue(all("/check-runs" in p for p, _, _ in api.writes))

    def test_api_failure_then_recovery(self):
        api = FakeAPI()
        self.assertEqual(self.review(api, error=gate.NotReviewed("API indisponível")), 1)
        self.assertIn("NÃO REVISADO", api.writes[-1][1]["output"]["summary"])
        self.assertEqual(self.review(api, {"decision": "APROVAR", "findings": []}), 0)

    def test_stale_result_cannot_approve(self):
        api = FakeAPI(stale=True)
        self.assertEqual(self.review(api, {"decision": "APROVAR", "findings": []}), 1)
        self.assertIn("OBSOLETA", api.writes[-1][1]["output"]["summary"])

    def test_override_current_sha(self):
        api = FakeAPI()
        self.assertEqual(gate.run(event(f"/gemini-override {HEAD} Falso positivo confirmado"), "issue_comment", api, "", "model"), 0)
        self.assertEqual(api.writes[-1][1]["conclusion"], "success")
        self.assertIn("issuecomment-123", api.writes[-1][1]["output"]["summary"])

    def test_override_wrong_sha_or_no_permission(self):
        for api, sha in [(FakeAPI(), "c" * 40), (FakeAPI(writable=False), HEAD)]:
            gate.run(event(f"/gemini-override {sha} Falso positivo confirmado"), "issue_comment", api, "", "model")
            self.assertFalse(api.writes)

    def test_command_must_be_explicit(self):
        for body in ["texto /gemini-recheck", "/gemini-recheck-more", f"/gemini-override {HEAD} curto"]:
            self.assertIsNone(gate.command(body)[0])

    def test_raw_model_output_never_published(self):
        f = finding(); f["reason"] = "SECRET_SENTINEL"; f["evidence"] = "SECRET_SENTINEL"
        api = FakeAPI()
        self.review(api, {"decision": "BLOQUEAR", "findings": [f]})
        self.assertNotIn("SECRET_SENTINEL", json.dumps(api.writes))

    def test_diff_limit_fails_instead_of_truncating(self):
        pr = FakeAPI().call("/pulls/19")
        with patch.object(gate, "git", side_effect=[b"", (HEAD + "\n").encode(), b"", b"x" * (gate.MAX_DIFF_BYTES + 1)]):
            with self.assertRaises(gate.NotReviewed):
                gate.collect_diff(pr)


if __name__ == "__main__":
    unittest.main()
