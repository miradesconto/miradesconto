"""Cliente mínimo da API Pinterest v5, sem exibir tokens ou corpos de erro."""
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def pinterest_request(access_token, path, payload=None):
    if not access_token:
        raise RuntimeError('PINTEREST_ACCESS_TOKEN ausente.')
    if not path.startswith('/') or '://' in path:
        raise ValueError('Caminho inválido de API.')
    data = json.dumps(payload).encode('utf-8') if payload is not None else None
    request = Request('https://api.pinterest.com/v5' + path, data=data,
                      headers={'Authorization': 'Bearer ' + access_token,
                               'Accept': 'application/json',
                               'Content-Type': 'application/json'},
                      method='POST' if data is not None else 'GET')
    try:
        with urlopen(request, timeout=25) as response:
            return json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f'Pinterest respondeu HTTP {exc.code}. Confira OAuth, permissões e conta Business.') from None
    except (URLError, TimeoutError, ValueError):
        raise RuntimeError('Falha de rede/resposta na API Pinterest.') from None


def find_existing_pin(access_token, article_url):
    """Falha fechado se não conseguir consultar a lista inteira."""
    bookmark = None
    seen_bookmarks = set()
    while True:
        params = {'page_size': 250}
        if bookmark:
            params['bookmark'] = bookmark
        page = pinterest_request(access_token, '/pins?' + urlencode(params))
        if not isinstance(page, dict) or not isinstance(page.get('items'), list):
            raise RuntimeError('Não foi possível reconciliar Pins já publicados.')
        for pin in page['items']:
            if isinstance(pin, dict) and str(pin.get('link', '')).rstrip('/') == article_url.rstrip('/'):
                return pin.get('id', 'existente')
        bookmark = page.get('bookmark')
        if not bookmark:
            return None
        if bookmark in seen_bookmarks:
            raise RuntimeError('Paginação repetida: publicação bloqueada.')
        seen_bookmarks.add(bookmark)
