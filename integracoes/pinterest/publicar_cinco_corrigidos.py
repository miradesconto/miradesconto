"""Publicação restrita às cinco artes finais aprovadas em 23/10/2026."""
import base64
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlencode

from api import pinterest_request
from publicar_lote import find_board

ROOT = Path(__file__).resolve().parents[2]

def normalize(link):
    return str(link or '').split('?')[0].rstrip('/')

def main():
    token = os.environ['PINTEREST_ACCESS_TOKEN'].strip()
    offers = json.loads((ROOT / 'integracoes/pinterest/cinco_corrigidos.json').read_text())
    if len(offers) != 5:
        raise RuntimeError('Lote precisa conter exatamente cinco artes finais.')
    for offer in offers:
        image = ROOT / offer['image']
        if hashlib.sha256(image.read_bytes()).hexdigest() != offer['sha256']:
            raise RuntimeError('Arte não corresponde à versão final aprovada.')
    board = find_board(token, 'Ofertas de Tecnologia e Achadinhos | MiraDesconto')
    existing = {}
    bookmark = None
    seen = set()
    while True:
        params = {'page_size': 250}
        if bookmark:
            params['bookmark'] = bookmark
        page = pinterest_request(token, '/pins?' + urlencode(params))
        if not isinstance(page.get('items'), list):
            raise RuntimeError('Não foi possível verificar Pins existentes.')
        for pin in page['items']:
            existing[normalize(pin.get('link'))] = pin.get('id')
        bookmark = page.get('bookmark')
        if not bookmark:
            break
        if bookmark in seen:
            raise RuntimeError('Paginação repetida; publicação bloqueada.')
        seen.add(bookmark)
    for offer in offers:
        duplicate = existing.get(normalize(offer['link'])) or existing.get(normalize(offer['affiliate']))
        if duplicate:
            print(f"IGNORADO JÁ EXISTE {offer['key']}: https://www.pinterest.com/pin/{duplicate}/", flush=True)
            continue
        payload = {
            'board_id': board,
            'title': offer['title'],
            'description': 'Confira os pontos de atenção antes de comprar no guia do MiraDesconto. Publicidade: conteúdo com links de afiliado; podemos receber comissão por compras elegíveis.',
            'link': offer['link'],
            'alt_text': offer['title'] + ' — arte branca e verde com logo MiraDesconto.',
            'media_source': {'source_type': 'image_base64', 'content_type': 'image/png', 'is_standard': True,
                             'data': base64.b64encode((ROOT / offer['image']).read_bytes()).decode('ascii')},
        }
        result = pinterest_request(token, '/pins', payload)
        pin_id = result.get('id')
        if not pin_id:
            raise RuntimeError('Resultado incerto: consultar Pinterest antes de qualquer nova tentativa.')
        print(f"PUBLICADO {offer['key']}: https://www.pinterest.com/pin/{pin_id}/", flush=True)
        check = pinterest_request(token, '/pins/' + str(pin_id))
        if normalize(check.get('link')) != normalize(offer['link']) or str(check.get('board_id')) != board:
            raise RuntimeError('Pin criado, mas verificação do destino falhou. Não repetir automaticamente.')
        existing[normalize(offer['link'])] = pin_id
        print('VERIFICADO ' + offer['key'], flush=True)

if __name__ == '__main__':
    main()
