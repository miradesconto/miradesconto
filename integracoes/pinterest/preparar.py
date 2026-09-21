"""Offline editorial drafts. No credentials, HTTP client or publishing endpoint."""
import argparse
import hashlib
import html
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
CONFIG = Path(__file__).with_name('config.json')


def metadata(path):
    text = path.read_text(encoding='utf-8')
    parts = text.split('---', 2)
    if len(parts) != 3 or parts[0].strip():
        raise ValueError(f'Artigo sem cabeçalho válido: {path.name}')
    return {k: json.loads(v.strip()) for line in parts[1].strip().splitlines()
            for k, v in [line.split(':', 1)]}


def build(root=ROOT, config=None, published_links=()):
    config = config or json.loads(CONFIG.read_text(encoding='utf-8'))
    if config.get('mode') != 'draft_only':
        raise ValueError('Somente o modo draft_only foi implementado.')
    base = config['siteUrl']
    if base != 'https://miradesconto.github.io/miradesconto/':
        raise ValueError('Destino não autorizado.')
    catalog = json.loads((root / 'dados/catalogo.json').read_text(encoding='utf-8'))
    products = {p['id']: p for p in catalog['products']}
    seen = set(published_links)
    posts = []
    for slug in config['articles']:
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', slug):
            raise ValueError('Identificador de artigo inválido.')
        meta = metadata(root / '_artigos' / (slug + '.md'))
        if meta.get('status') != 'publicado':
            raise ValueError(f'Artigo ainda não publicado: {slug}')
        link = base + 'blog/' + slug + '/'
        if link in seen:
            continue
        title = meta['title']
        if not isinstance(title, str) or not 1 <= len(title) <= 100:
            raise ValueError(f'Título exige revisão: {slug}')
        # Generic editorial copy deliberately avoids carrying price/stock claims.
        description = ('Leia a análise completa no MiraDesconto antes de decidir sua compra. '
                       'O site contém links de afiliados; podemos receber comissão por compras realizadas por esses links.')
        refs = [products[x] for x in meta['produtos'] if x in products]
        if not refs:
            raise ValueError(f'Artigo sem produto conhecido: {slug}')
        image = refs[0].get('imageUrl', '')
        if urlsplit(image).scheme != 'https' or not urlsplit(image).hostname:
            raise ValueError(f'Imagem de referência inválida: {slug}')
        seen.add(link)
        posts.append({
            'key': hashlib.sha256(link.encode()).hexdigest()[:20],
            'status': 'draft', 'approved': False, 'title': title,
            'description': description, 'link': link,
            'referenceImageUrl': image, 'boardId': None,
            'suggestedBoard': 'Moda e compras conscientes',
            'pending': ['Revisar texto', 'Criar e revisar arte final', 'Escolher pasta', 'Autorizar conta após aprovação da API']
        })
    return {'schemaVersion': 1, 'mode': 'draft_only', 'publishingEnabled': False, 'posts': posts}


def render(queue):
    esc = html.escape
    cards = []
    for p in queue['posts']:
        cards.append('<article><h2>' + esc(p['title']) + '</h2><p>' + esc(p['description'])
                     + '</p><p><a href="' + esc(p['link'], quote=True) + '">Abrir artigo</a></p>'
                     + '<p><a href="' + esc(p['referenceImageUrl'], quote=True) + '">Ver imagem de referência</a></p>'
                     + '<p>Pasta sugerida: ' + esc(p['suggestedBoard']) + '</p><ul>'
                     + ''.join('<li>' + esc(x) + '</li>' for x in p['pending']) + '</ul></article>')
    return ('<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Rascunhos MiraDesconto</title><style>body{font:17px/1.6 system-ui;background:#f1f5f9;color:#172033;max-width:850px;margin:auto;padding:24px}'
            'article{background:white;padding:24px;border-radius:16px;margin:20px 0}h1{line-height:1.2}a{color:#087c39}</style>'
            '<h1>Rascunhos para o Pinterest</h1><p>Publicação desativada. Nenhum Pin foi enviado. Imagens de referência ainda não são artes finais.</p>'
            + ''.join(cards) + '</html>')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT / 'preview/pinterest')
    parser.add_argument('--published-links', type=Path, help='Arquivo JSON com lista de URLs já publicadas; somente leitura.')
    args = parser.parse_args()
    links = json.loads(args.published_links.read_text(encoding='utf-8')) if args.published_links else []
    if not isinstance(links, list) or any(not isinstance(x, str) for x in links):
        raise ValueError('Histórico deve ser uma lista de URLs.')
    queue = build(published_links=links)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'fila.json').write_text(json.dumps(queue, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (args.output / 'revisao.html').write_text(render(queue), encoding='utf-8')
    print(f"OK: {len(queue['posts'])} rascunhos; publicação desativada.")


if __name__ == '__main__':
    main()
