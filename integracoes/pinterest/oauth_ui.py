"""Local-only OAuth setup. No publication endpoint, telemetry or credential logs."""
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import html
import secrets
import time
from urllib.parse import parse_qs, urlsplit
import webbrowser

import oauth_local as oauth

ORIGIN = 'http://localhost:8765'
ROOT = Path(__file__).resolve().parents[2]


def page(body):
    return ('''<!doctype html><html lang="pt-BR"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MiraDesconto — conectar Pinterest</title><style>
body{font:18px/1.6 system-ui;background:#f8fafc;color:#0f172a;margin:0}
main{max-width:760px;margin:50px auto;padding:32px;background:white;border-radius:20px}
h1{line-height:1.15}label{display:block;font-weight:700}input{box-sizing:border-box;width:100%;padding:14px;font:inherit;margin:12px 0}
button,a.cta{display:inline-block;padding:14px 20px;border:0;border-radius:9px;background:#15803d;color:white;font:inherit;text-decoration:none;cursor:pointer}
.note{padding:16px;background:#f0fdf4;border-radius:12px}small{color:#475569}img{max-width:250px;height:auto}
</style><main><strong>Mira<span style="color:#15803d">Desconto</span></strong>'''+body+'</main></html>').encode()


def create_server():
    csrf = secrets.token_urlsafe(32)
    session = {'state': None, 'secret': None, 'deadline': 0, 'result': None}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def handle_one_request(self):
            self.connection.settimeout(3)
            super().handle_one_request()

        def trusted_host(self):
            return self.headers.get('Host') == 'localhost:8765'

        def reply(self, status, body=b'', location=None, kind='text/html; charset=utf-8'):
            self.send_response(status)
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; img-src 'self'; form-action 'self'; frame-ancestors 'none'")
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(body)))
            if location:
                self.send_header('Location', location)
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if not self.trusted_host():
                self.reply(403)
                return
            parsed = urlsplit(self.path)
            if parsed.path == '/':
                self.reply(200, page('''<h1>Conectar sua conta ao Pinterest</h1>
<p class="note">App 1613942 · Trial ativo conferido em 08/10/2026.<br>Publicações automáticas desativadas.</p>
<p>Copie a chave do aplicativo no painel oficial e cole no campo protegido abaixo. Ela será usada somente para trocar a autorização com o Pinterest; não será gravada.</p>
<form method="post" action="/start"><input type="hidden" name="csrf" value="'''+csrf+'''">
<label for="secret">Chave secreta do aplicativo</label><input id="secret" type="password" name="secret" required autocomplete="off" maxlength="512">
<button>Continuar para o Pinterest</button></form>
<p><small>O Pinterest pedirá permissão para ler pastas e Pins e criar Pins. O aplicativo preparado aqui não tem função de publicação. Tokens recebidos ficam fora do repositório e, no Windows, criptografados para sua conta.</small></p>
<p><a href="https://developers.pinterest.com/apps/1613942/" target="_blank" rel="noreferrer">Abrir painel oficial do aplicativo</a></p>
<p><strong>Gravação:</strong> comece depois de preencher a chave. Filme a autorização oficial e a consulta de pastas. Não grave a chave nem a barra de endereço durante o retorno.</p>'''))
            elif parsed.path == '/callback':
                try:
                    if not session['state'] or time.monotonic() > session['deadline']:
                        raise ValueError('Sessao expirada')
                    code = oauth.validated_code(parse_qs(parsed.query), session['state'])
                except (ValueError, TypeError):
                    self.reply(400, page('<h1>Autorização inválida ou expirada</h1><p>Volte à tela inicial para tentar novamente.</p>'))
                    return
                session['state'] = None  # consume once, even if the token exchange fails
                try:
                    token = oauth.exchange_code(code, session['secret'])
                    oauth.store_private(token)
                    session['result'] = True
                except Exception:
                    session['result'] = False  # never render API bodies, errors or credentials
                finally:
                    session['secret'] = None
                self.reply(303, location='/done')
            elif parsed.path == '/done':
                if session['result'] is not True:
                    self.reply(200, page('<h1>Conexão não concluída</h1><p>Nenhum Pin foi enviado. Volte e autorize novamente.</p>'))
                    return
                self.reply(200, page('<h1>Pinterest conectado</h1><p>Autorização recebida e protegida. Nenhum Pin foi enviado.</p>'
                    '<form method="post" action="/check"><input type="hidden" name="csrf" value="'+csrf+'"><button>Consultar pastas pela API</button></form>'))
            elif parsed.path == '/pin.png':
                self.reply(200, (ROOT/'assets/pinterest/monitor-120-144.png').read_bytes(), kind='image/png')
            else:
                self.reply(404)

        def do_POST(self):
            if not self.trusted_host() or self.headers.get('Origin') != ORIGIN:
                self.reply(403)
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 4096:
                    raise ValueError()
                params = parse_qs(self.rfile.read(length).decode())
                if not secrets.compare_digest(params.get('csrf', [''])[0], csrf):
                    raise ValueError()
            except (ValueError, UnicodeError):
                self.reply(400)
                return
            if self.path == '/start':
                secret = params.get('secret', [''])[0].strip()
                if not secret or len(secret) > 512:
                    self.reply(400)
                    return
                session.update(secret=secret, state=secrets.token_urlsafe(32), deadline=time.monotonic()+600, result=None)
                self.reply(303, location=oauth.authorization_url(session['state']))
            elif self.path == '/check' and oauth.TOKEN_FILE.is_file():
                try:
                    items = oauth.list_boards()
                    rows = ''.join('<li>'+html.escape(str(x.get('name', 'Sem nome')))+' — ID '+html.escape(str(x.get('id', '')))+'</li>' for x in items)
                    self.reply(200, page('<h1>Consulta real concluída</h1><p>GET /v5/boards respondeu. Até 10 pastas desta página:</p><ul>'+rows+'</ul>'
                        '<p>Nenhum Pin foi enviado. Se a pasta não aparece nesta primeira página, será preciso consultar as próximas antes do teste.</p><h2>Pin preparado para revisão</h2><img src="/pin.png" alt="Guia de monitores 120 Hz ou 144 Hz">'
                        '<p><a href="https://miradesconto.com.br/blog/monitor-para-setup-como-comparar/">Abrir artigo de destino</a></p>'))
                except Exception:
                    self.reply(502, page('<h1>Consulta não concluída</h1><p>Confira a autorização e as permissões no Pinterest. Nenhum Pin foi enviado.</p>'))
            else:
                self.reply(404)

    return HTTPServer(('127.0.0.1', 8765), Handler)


def run(open_browser=True):
    server = create_server()
    print('Tela local pronta em http://localhost:8765/ — sem publicacao e sem logs de credenciais.', flush=True)
    if open_browser:
        webbrowser.open(ORIGIN+'/')
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == '__main__':
    run()
