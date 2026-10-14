"""Executar no computador do titular para autorizar sua própria conta Pinterest."""
from getpass import getpass
from http.server import BaseHTTPRequestHandler, HTTPServer
import secrets
import time
import webbrowser

from oauth_core import (REDIRECT_URI, authorization_url, callback_code,
                        gh_preflight, save_secret, token_request, verify_client_secret)


def main():
    gh_preflight()  # evitar consumir código OAuth se não conseguir acessar o GitHub
    app_secret = getpass('Cole a chave secreta do app Pinterest (não será exibida): ').strip()
    if not app_secret:
        raise RuntimeError('Chave secreta não informada.')
    print('Verificando chave do Pinterest antes de abrir o navegador...')
    verify_client_secret(app_secret)
    print('Chave validada; iniciando autorização de Pins.')
    state = secrets.token_urlsafe(32)
    received = {'code': None}

    class Callback(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass  # Nunca registrar códigos na URL.

        def do_GET(self):
            try:
                code = callback_code(self.path, state)
            except ValueError:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'Autorizacao invalida. Confira o terminal.')
                return
            received['code'] = code
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write('<h2>Autorização recebida.</h2><p>Volte ao terminal para confirmar o resultado.</p>'.encode('utf-8'))

    with HTTPServer(('127.0.0.1', 8765), Callback) as server:
        server.timeout = 4
        url = authorization_url(state)
        print('Abrindo Pinterest para autorização... (aguarde até 4 minutos)')
        if not webbrowser.open(url):
            print('Abra o link abaixo manualmente (não compartilhe):')
            print(url)
        expires = time.monotonic() + 240
        while not received['code'] and time.monotonic() < expires:
            server.handle_request()
    if not received['code']:
        raise RuntimeError('Autorização expirou. Execute novamente.')
    result = token_request(app_secret, {
        'grant_type': 'authorization_code', 'code': received['code'],
        'redirect_uri': REDIRECT_URI
    })
    granted = set(str(result.get('scope', '')).replace(',', ' ').split())
    if granted and not {'pins:write', 'pins:read', 'boards:read'} <= granted:
        raise RuntimeError('Permissões OAuth incompletas; autorize os escopos exigidos.')
    # Rotação: salve o refresh primeiro. Nunca imprima os valores.
    save_secret('PINTEREST_REFRESH_TOKEN', result['refresh_token'])
    save_secret('PINTEREST_ACCESS_TOKEN', result['access_token'])
    print('OK: Pinterest autorizado; tokens guardados em GitHub Actions Secrets.')
    print('Agora execute o workflow "Pinterest — validar conexão" no GitHub.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError) as exc:
        print('ERRO:', str(exc))
        raise SystemExit(1)
