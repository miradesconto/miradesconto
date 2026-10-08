"""Autorizacao OAuth local do Pinterest; nao publica Pins.

Executar apenas no computador do titular. Nunca copie client secret, codigos
OAuth ou tokens para issues, chats, logs ou arquivos do repositorio.
"""
import base64
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import secrets
import sys
import tempfile
import time
from urllib import error, parse, request
import webbrowser

APP_ID = '1613942'  # ID publico do MiraDesconto Publicador
CALLBACK = 'http://127.0.0.1:8765/callback'
SCOPES = 'boards:read,pins:read,pins:write'
PRIVATE_DIR = Path.home() / '.miradesconto' / 'pinterest'
TOKEN_FILE = PRIVATE_DIR / 'oauth.json'


def authorization_url(state):
    return 'https://www.pinterest.com/oauth/?' + parse.urlencode({
        'client_id': APP_ID,
        'redirect_uri': CALLBACK,
        'response_type': 'code',
        'scope': SCOPES,
        'state': state,
    })


def validated_code(params, expected_state):
    states = params.get('state', [])
    codes = params.get('code', [])
    if len(states) != 1 or not secrets.compare_digest(states[0], expected_state):
        raise ValueError('OAuth state nao corresponde: autorizacao recusada.')
    if len(codes) != 1 or not codes[0]:
        raise ValueError('Codigo de autorizacao ausente.')
    return codes[0]


def store_private(data):
    PRIVATE_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        os.chmod(PRIVATE_DIR, 0o700)
    except OSError:
        pass  # ACL do usuario Windows precisa ser protegida pelo sistema
    fd, temp_name = tempfile.mkstemp(prefix='.oauth-', dir=PRIVATE_DIR)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as output:
            json.dump(data, output)
            output.write('\n')
        try:
            os.chmod(temp_name, 0o600)
        except OSError:
            pass
        os.replace(temp_name, TOKEN_FILE)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def exchange_code(code, app_secret):
    credentials = base64.b64encode((APP_ID + ':' + app_secret).encode()).decode()
    body = parse.urlencode({
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': CALLBACK,
    }).encode()
    req = request.Request(
        'https://api.pinterest.com/v5/oauth/token',
        data=body,
        headers={
            'Authorization': 'Basic ' + credentials,
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
        }, method='POST')
    try:
        with request.urlopen(req, timeout=25) as response:
            payload = json.load(response)
    except error.HTTPError as exc:
        # Never include API response bodies: they may contain secrets.
        raise RuntimeError(f'Troca OAuth recusada (HTTP {exc.code}).') from None
    if not isinstance(payload, dict) or not payload.get('access_token'):
        raise RuntimeError('Resposta da API sem access_token.')
    return payload


def authorize():
    app_secret = os.environ.get('PINTEREST_APP_SECRET')
    if not app_secret:
        raise RuntimeError('Defina PINTEREST_APP_SECRET no ambiente privado antes da execucao.')
    state = secrets.token_urlsafe(32)

    class CallbackHandler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Evita registrar caminho, codigo e state do callback.

        def do_GET(self):
            parsed = parse.urlsplit(self.path)
            if parsed.path != '/callback':
                self.send_error(404)
                return
            params = parse.parse_qs(parsed.query)
            try:
                self.server.authorization_code = validated_code(params, state)
                status, msg = 200, 'Autorizacao recebida. Pode fechar esta aba.'
            except ValueError:
                status, msg = 400, 'Autorizacao invalida. Volte ao aplicativo.'
            self.send_response(status)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.end_headers()
            self.wfile.write(msg.encode('utf-8'))

    server = HTTPServer(('127.0.0.1', 8765), CallbackHandler)
    server.timeout = 1
    server.authorization_code = None
    try:
        url = authorization_url(state)
        print('Abrindo Pinterest para autorizacao OAuth. Nenhum Pin sera publicado.')
        if not webbrowser.open(url):
            print('Abra manualmente o link abaixo, apenas em seu computador:')
            print(url)
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline and not server.authorization_code:
            server.handle_request()
        if not server.authorization_code:
            raise TimeoutError('Autorizacao nao recebida em 3 minutos.')
    finally:
        server.server_close()

    token = exchange_code(server.authorization_code, app_secret)
    store_private(token)
    print('OAuth concluido; token salvo no perfil privado deste computador.')
    print('Escopos retornados:', token.get('scope', 'verifique no painel'))
    print('Tokens e refresh_token nao serao exibidos.')


def check():
    if not TOKEN_FILE.is_file():
        raise RuntimeError('Autorizacao ausente: execute primeiro o comando authorize.')
    token = json.loads(TOKEN_FILE.read_text(encoding='utf-8')).get('access_token')
    if not token:
        raise RuntimeError('Token de acesso nao encontrado.')
    req = request.Request(
        'https://api.pinterest.com/v5/boards?page_size=10',
        headers={'Authorization': 'Bearer ' + token, 'Accept': 'application/json'})
    try:
        with request.urlopen(req, timeout=25) as response:
            data = json.load(response)
    except error.HTTPError as exc:
        raise RuntimeError(f'Consulta de pastas falhou (HTTP {exc.code}).') from None
    items = data.get('items', [])
    print(f'API Pinterest respondeu: {len(items)} pasta(s) nesta pagina.')
    for item in items:
        print('Pasta:', item.get('name', '(sem nome)'), '— ID:', item.get('id', '(sem ID)'))


if __name__ == '__main__':
    try:
        if len(sys.argv) != 2 or sys.argv[1] not in ('authorize', 'check'):
            raise ValueError('Uso: python integracoes/pinterest/oauth_local.py authorize|check')
        {'authorize': authorize, 'check': check}[sys.argv[1]]()
    except (ValueError, RuntimeError, TimeoutError, OSError, error.URLError) as exc:
        print('Erro:', str(exc), file=sys.stderr)
        sys.exit(1)
