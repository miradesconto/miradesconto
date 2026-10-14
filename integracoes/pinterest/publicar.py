"""Publicação única revisada: somente acionamento manual e URL no site próprio."""
import argparse
import os
import re
from urllib.parse import urlsplit
from pathlib import Path
from api import pinterest_request, find_existing_pin
from preparar import metadata

ROOT = Path(__file__).resolve().parents[2]
SITE = 'https://miradesconto.com.br'


def validate_inputs(slug, board_id, image_url, confirmation):
    if confirmation != 'PUBLICAR':
        raise ValueError('Confirmação explícita PUBLICAR obrigatória.')
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', slug):
        raise ValueError('Slug inválido.')
    if not re.fullmatch(r'[0-9]{5,30}', board_id):
        raise ValueError('ID de pasta Pinterest inválido.')
    parsed = urlsplit(image_url)
    if (parsed.scheme != 'https' or parsed.hostname != 'miradesconto.com.br'
            or parsed.username or parsed.password or parsed.port or parsed.query
            or parsed.fragment or not re.search(r'\.(png|jpe?g)$', parsed.path, re.I)):
        raise ValueError('Arte final precisa ser PNG/JPG HTTPS hospedada no MiraDesconto.')
    item = ROOT / '_artigos' / (slug + '.md')
    if not item.is_file():
        raise ValueError('Artigo não encontrado na main.')
    meta = metadata(item)
    if meta.get('status') != 'publicado' or meta.get('published') is not True:
        raise ValueError('Artigo não publicado: envio bloqueado.')
    title = meta.get('title')
    if not isinstance(title, str) or not 1 <= len(title) <= 100:
        raise ValueError('Título fora do limite; revise o artigo.')
    return title, SITE + '/blog/' + slug + '/'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--article', required=True)
    parser.add_argument('--board-id', required=True)
    parser.add_argument('--image-url', required=True)
    parser.add_argument('--confirmation', required=True)
    args = parser.parse_args()
    title, link = validate_inputs(args.article, args.board_id, args.image_url, args.confirmation)
    token = os.getenv('PINTEREST_ACCESS_TOKEN', '').strip()
    if not token:
        raise RuntimeError('Falta PINTEREST_ACCESS_TOKEN. Execute primeiro o OAuth.')
    existing = find_existing_pin(token, link)
    if existing:
        print('Ignorado: já existe Pin do mesmo artigo na conta (ID: ' + str(existing) + ').')
        return
    payload = {
        'board_id': args.board_id, 'link': link, 'title': title,
        'description': ('Leia o guia completo no MiraDesconto. Conteúdo editorial '
                        'com links de afiliados; podemos receber comissão em compras elegíveis.'),
        'media_source': {'source_type': 'image_url', 'url': args.image_url, 'is_standard': True}
    }
    created = pinterest_request(token, '/pins', payload)
    if not isinstance(created, dict) or not created.get('id'):
        raise RuntimeError('Resposta incerta: verifique manualmente o Pinterest ANTES de repetir.')
    print('Pin criado com sucesso; ID: ' + str(created['id']))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, RuntimeError, OSError) as exc:
        print('ERRO:', str(exc))
        raise SystemExit(1)
