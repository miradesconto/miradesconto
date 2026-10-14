"""OAuth Pinterest v5. Nunca registrar segredos, códigos ou respostas brutas."""
import base64
import json
import os
import shutil
import subprocess
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, parse_qs, urlsplit
from urllib.request import Request, urlopen
import hmac

APP_ID = '1613942'
REPO = 'miradesconto/miradesconto'
REDIRECT_URI = 'http://localhost:8765/callback'
SCOPES = ('boards:read', 'pins:read', 'pins:write', 'boards:write', 'user_accounts:read')
TOKEN_URL = 'https://api.pinterest.com/v5/oauth/token'


def authorization_url(state):
    if not isinstance(state, str) or len(state) < 20:
        raise ValueError('O state OAuth precisa ser aleatório e forte.')
    params = {
        'client_id': APP_ID, 'redirect_uri': REDIRECT_URI,
        'response_type': 'code', 'scope': ','.join(SCOPES), 'state': state
    }
    return 'https://www.pinterest.com/oauth/?' + urlencode(params)


def callback_code(target, expected_state):
    parsed = urlsplit(target)
    if parsed.path != '/callback':
        raise ValueError('Caminho de retorno inesperado.')
    qs = parse_qs(parsed.query)
    state = qs.get('state', [''])[0]
    if not hmac.compare_digest(state, expected_state):
        raise ValueError('State OAuth não corresponde ao solicitado.')
    if qs.get('error'):
        raise ValueError('Autorização recusada no Pinterest.')
    code = qs.get('code', [''])[0]
    if not code:
        raise ValueError('Pinterest não enviou código de autorização.')
    return code


def token_request(app_secret, payload, opener=urlopen, require_refresh=True):
    if not app_secret:
        raise ValueError('Chave secreta ausente.')
    auth = base64.b64encode((APP_ID + ':' + app_secret).encode('utf-8')).decode('ascii')
    body = urlencode(payload).encode('utf-8')
    request = Request(
        TOKEN_URL, data=body,
        headers={'Authorization': 'Basic ' + auth,
                 'Content-Type': 'application/x-www-form-urlencoded'},
        method='POST'
    )
    try:
        with opener(request, timeout=25) as response:
            result = json.load(response)
    except HTTPError as exc:
        if exc.code == 401:
            raise RuntimeError('Pinterest recusou as credenciais do aplicativo (HTTP 401). Confira a chave secreta atual do app 1613942, não o token de teste.') from None
        raise RuntimeError(f'Pinterest recusou o OAuth (HTTP {exc.code}). Confira o código e a URI de retorno.') from None
    except (URLError, TimeoutError, ValueError):
        raise RuntimeError('Falha ao consultar OAuth do Pinterest; confira a conexão.') from None
    if (not isinstance(result, dict)
            or not isinstance(result.get('access_token'), str)
            or not result['access_token']):
        raise RuntimeError('Pinterest não retornou um token de acesso válido.')
    if require_refresh and (not isinstance(result.get('refresh_token'), str)
                            or not result['refresh_token']):
        raise RuntimeError('Pinterest não retornou o refresh token esperado.')
    return result


def verify_client_secret(app_secret):
    """Verifica credenciais com token app-only, sem exibir nem guardar o token."""
    token_request(app_secret, {'grant_type': 'client_credentials',
                               'scope': 'boards:read'}, require_refresh=False)
    return True


def gh_preflight():
    if not shutil.which('gh'):
        raise RuntimeError('Instale o GitHub CLI (gh) antes da autorização.')
    proc = subprocess.run(['gh', 'auth', 'status', '-h', 'github.com'],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    if proc.returncode:
        raise RuntimeError('Entre no GitHub CLI primeiro: gh auth login')


def save_secret(name, value):
    if name not in {'PINTEREST_ACCESS_TOKEN', 'PINTEREST_REFRESH_TOKEN'}:
        raise ValueError('Nome de secret não permitido.')
    if not value:
        raise ValueError('Token vazio.')
    result = subprocess.run(
        ['gh', 'secret', 'set', name, '--repo', REPO], input=value,
        text=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        check=False
    )
    if result.returncode:
        raise RuntimeError(f'Falha ao salvar {name} no GitHub (confira as permissões).')


def mask_for_actions(value):
    # GitHub Actions interpreta comandos em stdout; escapar caracteres reservados.
    value = value.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
    print('::add-mask::' + value, flush=True)
