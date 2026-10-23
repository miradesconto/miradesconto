"""Corrige somente o destino de Pins existentes do Acer, sem criar Pins."""
import json
import os
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from api import pinterest_request
from publicar_lote import find_board

NEW = 'https://meli.la/2HFXYWD'
OLD = 'https://meli.la/1zsVjAj'

def main():
    token = os.environ['PINTEREST_ACCESS_TOKEN']
    board = find_board(token, 'Ofertas de Tecnologia e Achadinhos | MiraDesconto')
    bookmark = None
    seen = set()
    matches = []
    while True:
        params = {'page_size': 250}
        if bookmark:
            params['bookmark'] = bookmark
        page = pinterest_request(token, '/boards/' + board + '/pins?' + urlencode(params))
        if not isinstance(page.get('items'), list):
            raise RuntimeError('Consulta de Pins incompleta; nenhuma alteração.')
        for pin in page['items']:
            title = str(pin.get('title', '')).casefold()
            if str(pin.get('link', '')).rstrip('/') in (OLD, NEW) or title == 'notebook acer aspire go i7: o que conferir na configuração':
                matches.append(pin)
        bookmark = page.get('bookmark')
        if not bookmark:
            break
        if bookmark in seen:
            raise RuntimeError('Paginação repetida.')
        seen.add(bookmark)
    if not matches:
        raise RuntimeError('Pin Acer não encontrado. Nenhum Pin criado.')
    for pin in matches:
        pid = str(pin['id'])
        if pin.get('link') != NEW:
            req = Request('https://api.pinterest.com/v5/pins/' + pid,
                          data=json.dumps({'link': NEW}).encode(), method='PATCH',
                          headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
            try:
                with urlopen(req, timeout=25) as response:
                    json.load(response)
            except HTTPError as exc:
                raise RuntimeError('Atualização Pinterest HTTP ' + str(exc.code)) from None
        current = pinterest_request(token, '/pins/' + pid)
        if current.get('link') != NEW:
            raise RuntimeError('Destino não confirmado; não criar outro Pin.')
        print('CORRIGIDO E VERIFICADO https://www.pinterest.com/pin/' + pid + '/ -> ' + NEW, flush=True)

if __name__ == '__main__':
    main()
