"""Publica um único Pin revisado: artigo do site OU produto afiliado do Mercado Livre."""
import argparse
import os
import re
from pathlib import Path
from urllib.parse import urlsplit

from api import pinterest_request, find_existing_pin
from link_rules import affiliate_description, validate_ml_link
from preparar import metadata

ROOT = Path(__file__).resolve().parents[2]
SITE = 'https://miradesconto.com.br'
SITE_DESCRIPTION = (
    'Leia o guia completo no MiraDesconto. Conteúdo editorial '
    'com links de afiliados; podemos receber comissão em compras elegíveis.'
)


def validate_common(board_id, image_url, confirmation):
    if confirmation != 'PUBLICAR':
        raise ValueError('Confirmação explícita PUBLICAR obrigatória.')
    if not re.fullmatch(r'[0-9]{5,30}', board_id):
        raise ValueError('ID de pasta Pinterest inválido.')
    parsed = urlsplit(image_url)
    if (parsed.scheme != 'https' or parsed.hostname != 'miradesconto.com.br'
            or parsed.username or parsed.password or parsed.port or parsed.query
            or parsed.fragment or not re.search(r'\.(png|jpe?g)$', parsed.path, re.I)):
        raise ValueError('Arte final precisa ser PNG/JPG HTTPS hospedada no MiraDesconto.')


def validate_inputs(slug, board_id, image_url, confirmation):
    """Validação original dos artigos (mantida para compatibilidade)."""
    validate_common(board_id, image_url, confirmation)
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', slug):
        raise ValueError('Slug inválido.')
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


def validate_publication(destination, article, affiliate_url, affiliate_title, caption,
                         board_id, image_url, confirmation):
    """Cada tipo de Pin exige um único destino, evitando link trocado sem perceber."""
    if destination == 'site':
        if affiliate_url or affiliate_title or caption:
            raise ValueError('Para artigo do site, deixe os campos de afiliado vazios.')
        title, link = validate_inputs(article, board_id, image_url, confirmation)
        return title, link, SITE_DESCRIPTION
    if destination == 'mercado_livre':
        validate_common(board_id, image_url, confirmation)
        if article:
            raise ValueError('Para Mercado Livre, deixe o campo de artigo vazio.')
        link = validate_ml_link(affiliate_url)
        if (not isinstance(affiliate_title, str)
                or affiliate_title != affiliate_title.strip()
                or re.search(r'[\x00-\x1f\x7f]', affiliate_title)
                or not 1 <= len(affiliate_title) <= 100):
            raise ValueError('Título de produto inválido (1 a 100 caracteres).')
        description = affiliate_description(caption)
        return affiliate_title, link, description
    raise ValueError('Destino inválido: selecione site ou mercado_livre.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--destination', choices=['site', 'mercado_livre'], default='site')
    parser.add_argument('--article', default='')
    parser.add_argument('--affiliate-url', default='')
    parser.add_argument('--affiliate-title', default='')
    parser.add_argument('--caption', default='')
    parser.add_argument('--board-id', required=True)
    parser.add_argument('--image-url', required=True)
    parser.add_argument('--confirmation', required=True)
    args = parser.parse_args()
    title, link, description = validate_publication(
        args.destination, args.article, args.affiliate_url, args.affiliate_title,
        args.caption, args.board_id, args.image_url, args.confirmation
    )
    token = os.getenv('PINTEREST_ACCESS_TOKEN', '').strip()
    if not token:
        raise RuntimeError('Falta PINTEREST_ACCESS_TOKEN. Execute primeiro o OAuth.')
    existing = find_existing_pin(token, link)
    if existing:
        print('Ignorado: já existe Pin para este destino (ID: ' + str(existing) + ').')
        return
    payload = {
        'board_id': args.board_id, 'link': link, 'title': title,
        'description': description,
        'media_source': {'source_type': 'image_url', 'url': args.image_url,
                         'is_standard': True}
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
