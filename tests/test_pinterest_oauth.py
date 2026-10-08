import importlib.util
from pathlib import Path
import unittest
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('pinterest_oauth', ROOT / 'integracoes/pinterest/oauth_local.py')
oauth = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oauth)


class OAuthLocalTests(unittest.TestCase):
    def test_authorization_url_requests_only_needed_scopes(self):
        url = urlsplit(oauth.authorization_url('state-test'))
        self.assertEqual(url.netloc, 'www.pinterest.com')
        self.assertEqual(url.path, '/oauth/')
        params = parse_qs(url.query)
        self.assertEqual(params['redirect_uri'], ['http://localhost:8765/callback'])
        self.assertEqual(params['scope'], ['boards:read,pins:read,pins:write'])
        self.assertEqual(params['response_type'], ['code'])
        self.assertEqual(params['state'], ['state-test'])

    def test_callback_state_is_verified_before_accepting_code(self):
        self.assertEqual(oauth.validated_code({'code': ['test-code'], 'state': ['right']}, 'right'), 'test-code')
        for params in (
            {'code': ['test-code'], 'state': ['wrong']},
            {'code': ['test-code']},
            {'code': ['test-code'], 'state': ['right', 'right']},
            {'code': [''], 'state': ['right']},
            {'state': ['right']},
        ):
            with self.assertRaises(ValueError):
                oauth.validated_code(params, 'right')


if __name__ == '__main__':
    unittest.main()
