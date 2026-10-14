import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_DIR = ROOT / 'integracoes' / 'pinterest'
spec = importlib.util.spec_from_file_location('oauth_core', MODULE_DIR / 'oauth_core.py')
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)


class PinterestOAuthTests(unittest.TestCase):
    def test_authorize_link_has_expected_scope_and_exact_callback(self):
        from urllib.parse import parse_qs, urlsplit
        url = core.authorization_url('z' * 32)
        self.assertEqual(urlsplit(url).netloc, 'www.pinterest.com')
        params = parse_qs(urlsplit(url).query)
        self.assertEqual(params['client_id'], ['1613942'])
        self.assertEqual(params['redirect_uri'], ['http://localhost:8765/callback'])
        self.assertIn('pins:write', params['scope'][0])

    def test_state_is_required_and_checked(self):
        with self.assertRaises(ValueError):
            core.authorization_url('weak')
        self.assertEqual(core.callback_code('/callback?code=abc&state=' + 'a' * 32, 'a' * 32), 'abc')
        with self.assertRaisesRegex(ValueError, 'State'):
            core.callback_code('/callback?code=abc&state=wrong', 'a' * 32)
        with self.assertRaises(ValueError):
            core.callback_code('/callback?state=' + 'a' * 32, 'a' * 32)
        with self.assertRaises(ValueError):
            core.callback_code('/other?code=abc&state=' + 'a' * 32, 'a' * 32)

    def test_publishing_requires_review_and_owned_image(self):
        spec = importlib.util.spec_from_file_location('preparar', MODULE_DIR / 'preparar.py')
        import sys
        # importar módulos irmãos sem redes ou dependências adicionais
        sys.path.insert(0, str(MODULE_DIR))
        try:
            import publicar
            with self.assertRaisesRegex(ValueError, 'PUBLICAR'):
                publicar.validate_inputs('iphone-15-ou-16-em-promocao', '123456789', 'https://miradesconto.com.br/pin.jpg', '')
            with self.assertRaises(ValueError):
                publicar.validate_inputs('iphone-15-ou-16-em-promocao', '123456789', 'https://site-externo.com/pin.jpg', 'PUBLICAR')
            title, link = publicar.validate_inputs('iphone-15-ou-16-em-promocao', '123456789', 'https://miradesconto.com.br/pin.jpg', 'PUBLICAR')
            self.assertTrue(title)
            self.assertEqual(link, 'https://miradesconto.com.br/blog/iphone-15-ou-16-em-promocao/')
        finally:
            sys.path.remove(str(MODULE_DIR))
    def test_check_secret_accepts_app_token_without_refresh_token(self):
        from io import BytesIO
        import json
        seen = []
        def fake_open(request, timeout):
            seen.append(request)
            return BytesIO(json.dumps({'access_token': 'pinc-test'}).encode())
        result = core.token_request('not-a-real-secret',
                                    {'grant_type': 'client_credentials', 'scope': 'boards:read'},
                                    opener=fake_open, require_refresh=False)
        self.assertEqual(result['access_token'], 'pinc-test')
        self.assertIn('Basic ', seen[0].get_header('Authorization'))
        with self.assertRaisesRegex(RuntimeError, 'refresh token'):
            core.token_request('not-a-real-secret',
                               {'grant_type': 'authorization_code', 'code': 'fake'},
                               opener=fake_open)

    def test_rejected_client_secret_has_safe_message(self):
        from urllib.error import HTTPError
        def fake_open(_request, timeout):
            raise HTTPError('https://api.pinterest.com/v5/oauth/token', 401, 'Unauthorized', {}, None)
        with self.assertRaisesRegex(RuntimeError, 'chave secreta atual'):
            core.token_request('a-secret-that-must-not-leak', {'grant_type': 'client_credentials'},
                               opener=fake_open, require_refresh=False)


if __name__ == '__main__':
    unittest.main()
