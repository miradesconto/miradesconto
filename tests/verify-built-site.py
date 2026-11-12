"""Validate actual Jekyll output, including links, canonicals and JSON-LD."""
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
from xml.etree import ElementTree

root=Path(sys.argv[1] if len(sys.argv)>1 else '_site')
base=''
origin='https://miradesconto.com.br'
class Page(HTMLParser):
    def __init__(self,text):
        super().__init__();self.links=[];self.ids=set();self.h1=0;self.canonical=[];self.description=[];self.schema=[];self.in_schema=False;self.buffer='';self.feed(text)
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if a.get('id'):self.ids.add(a['id'])
        if tag=='h1':self.h1+=1
        if tag=='a' and a.get('href'):self.links.append(a['href'])
        if tag=='link' and a.get('rel')=='canonical':self.canonical.append(a['href'])
        if tag=='meta' and a.get('name')=='description':self.description.append(a.get('content'))
        if tag=='script' and a.get('type')=='application/ld+json':self.in_schema=True;self.buffer=''
    def handle_data(self,data):
        if self.in_schema:self.buffer+=data
    def handle_endtag(self,tag):
        if tag=='script' and self.in_schema:self.schema.append(json.loads(self.buffer));self.in_schema=False

pages={}
for file in root.rglob('*.html'):
    text=file.read_text(encoding='utf-8')
    assert '{{' not in text and '{%' not in text, f'Unrendered Liquid: {file}'
    pages[file.relative_to(root).as_posix()]=Page(text)
sitemap=ElementTree.parse(root/'sitemap.xml')
urls=[e.text for e in sitemap.findall('.//{*}loc')]
assert len(urls)==len(set(urls)), 'Sitemap contains duplicate URLs'
source=Path(__file__).resolve().parents[1]
for file in (source/'_compras').glob('*.md'):
    front=file.read_text(encoding='utf-8').split('---')[1]
    meta={k:json.loads(v) for k,v in (line.split(': ',1) for line in front.strip().splitlines())}
    url=origin+base+meta['permalink'];key=meta['permalink'].lstrip('/')+'index.html';p=pages[key]
    assert p.h1==1 and p.canonical==[url] and len(p.description)==1 and p.description[0],key
    assert url in urls,key
    assert {s['@type'] for s in p.schema} >= {meta['schema'],'BreadcrumbList'},key
    for href in p.links:
        u=urlsplit(href)
        if u.scheme or u.netloc:continue
        target=unquote(u.path)
        if not target:target=base+meta['permalink']
        assert target.startswith(base+'/'),(key,href)
        local=target[len(base)+1:]
        if local.endswith('/'):local+='index.html'
        assert (root/local).exists(),(key,href)
        if u.fragment and local in pages:assert u.fragment in pages[local].ids,(key,href)
print('OK: 10 rendered pages, H1, descriptions, canonicals, schema, sitemap, internal links and anchors')

# Editorial discovery must lead to published, indexable articles and valid offers.
from posixpath import normpath
editorial=['blog/index.html']
for file in (source/'_artigos').glob('*.md'):
    front=file.read_text(encoding='utf-8').split('---')[1]
    if 'status: "publicado"' in front:
        editorial.append('blog/'+file.stem+'/index.html')
for key in editorial:
    p=pages[key];url=origin+base+'/'+key.removesuffix('index.html')
    assert p.h1==1 and p.canonical==[url] and len(p.description)==1 and p.description[0],key
    assert url in urls and p.schema,key
    for href in p.links:
        u=urlsplit(href)
        if u.scheme or u.netloc:continue
        target=unquote(u.path)
        if target.startswith('/'):
            assert target.startswith(base+'/'),(key,href)
            local=target[len(base)+1:]
        elif target:
            local=normpath(str(Path(key).parent.as_posix())+'/'+target)
            if target.endswith('/'):local+='/'
        else:local=key
        if local.endswith('/'):local+='index.html'
        assert (root/local).exists(),(key,href)
        if u.fragment and local in pages:assert u.fragment in pages[local].ids,(key,href)
print(f'OK: blog and {len(editorial)-1} published articles, metadata, sitemap and internal paths')

# Drafts must not leak through discovery, and known affiliate lists need honest labels.
for file in (source/'_artigos').glob('*.md'):
    front=file.read_text(encoding='utf-8').split('---')[1]
    if 'status: "rascunho"' in front:
        draft_url=origin+'/blog/'+file.stem+'/'
        assert draft_url not in urls, draft_url
        assert '/blog/'+file.stem+'/' not in pages['blog/index.html'].links, draft_url
notebooks=(root/'blog/notebook-em-promocao-como-escolher/index.html').read_text(encoding='utf-8')
assert 'Abrir lista na loja' in notebooks
assert 'Link de afiliado para uma lista.' in notebooks
for key in editorial + ['radar/index.html']:
    text=(root/key).read_text(encoding='utf-8')
    assert 'blog.js?v=20261013audit' in text, f'Image recovery missing: {key}'
# The public sections share one menu and keep their landing page purpose.
main_routes = ['/', '/black-friday/', '/catalogo/', '/radar/', '/blog/', '/sobre.html']
main_menu = ['/', '/blog/', '/sobre.html']
def route_file(route):
    return route.lstrip('/') + ('index.html' if route.endswith('/') else '')

menu_pages = [route_file(route) for route in main_routes]
other_pages = ['transparencia.html', 'privacidade.html', 'shopee-gamer/index.html']
for key in menu_pages + other_pages + editorial[1:]:
    page_text = (root / key).read_text(encoding='utf-8')
    menu = re.search(r'<nav class="mira-global-nav"[^>]*>(.*?)</nav>', page_text, re.S)
    assert menu and re.findall(r'href="([^"]+)"', menu[1]) == main_menu, key
    if key in menu_pages:
        route = main_routes[menu_pages.index(key)]
        if route in main_menu:
            assert f'href="{route}" aria-current="page"' in menu[1], key
        else:
            # Catálogo, Radar e campanhas compartilham a seção Ofertas.
            assert 'href="/" aria-current="location"' in menu[1], key

for key in menu_pages + other_pages + ['en/index.html', 'en/blog/index.html']:
    assert pages[key].h1 == 1, key
    for href in pages[key].links:
        u = urlsplit(href)
        if u.scheme or u.netloc:
            continue
        target = unquote(u.path)
        local = target.lstrip('/') if target.startswith('/') else normpath(str(Path(key).parent / target)) if target else key
        if target.endswith('/') or local == '.':
            local = local.rstrip('/') + '/index.html' if local not in ('', '.') else 'index.html'
        assert (root / local).exists(), (key, href)
        if u.fragment and local in pages:
            assert u.fragment in pages[local].ids, (key, href)

for key in ('blog/index.html', 'en/blog/index.html'):
    page_text = (root / key).read_text(encoding='utf-8')
    for marker in ('vitrine-diaria', 'auto-ofertas', 'shopee-highlights', 'mira-shop-entry', 'editorial-shop-cta'):
        assert marker not in page_text, (key, marker)
print('OK: menu, active page, public links and editorial boundaries')

# A full catalogue must be linked from the compact homepage and indexed.
catalog_key='catalogo/index.html'
catalog_page=pages[catalog_key]
assert catalog_page.h1==1 and catalog_page.canonical==[origin+'/catalogo/'], catalog_key
assert len(catalog_page.description)==1 and catalog_page.description[0], catalog_key
assert origin+'/catalogo/' in urls, catalog_key
assert 'catalogo/' in pages['index.html'].links, 'Missing visible catalogue entry point'
print('OK: catalogue navigation, sitemap, metadata, internal paths')


# Smoke test: 4 PT cards still use the original curated Liquid component.
from html import unescape
radar_source = json.loads((source / '_data' / 'radar.json').read_text(encoding='utf-8'))
pt_html = (root / 'index.html').read_text(encoding='utf-8')
pt_cards = re.findall(r'<article class="vitrine-card[^"]*" data-vitrine-id="([^"]+)"[^>]*>(.*?)</article>', pt_html, re.S)
assert len(pt_cards) == 4, f'PT: expected 4 curated cards, found {len(pt_cards)}'
for product_id, body in pt_cards:
    product = radar_source['byId'].get(product_id)
    assert product, (product_id, 'not in radar')
    assert 'Ver Oferta' in body and 'data-item-id="' + product_id + '"' in body
    assert len(re.findall(r'class="vitrine-spec"', body)) <= 3
    title = re.search(r'<h3[^>]*>(.*?)</h3>', body, re.S)
    assert title and len(unescape(title.group(1)).strip()) <= 55
    if product.get('currentPriceText'):
        assert product['currentPriceText'] in unescape(body)
# A seleção é rotativa: não exigir que um ID antigo esteja entre os quatro cards.
# Conferir a identidade do produto e o CTA real em todos os cards exibidos.
for product_id, body in pt_cards:
    product = radar_source['byId'][product_id]
    item_name = re.search(r'data-item-name="([^"]+)"', body)
    assert item_name and unescape(item_name.group(1)) == product['name'], (product_id, 'product identity changed')
    cta = re.search(r'<a class="vitrine-cta"[^>]*href="([^"]+)"', body, re.S)
    assert cta and re.fullmatch(r'https://meli\.la/[A-Za-z0-9]+', unescape(cta.group(1))), (product_id, 'invalid affiliate CTA')
print('OK: 4 curated PT cards with correct data and CTA')

# EN now uses independent observed-price cards, linking actual radar items
# and dedicated English buying guides instead of copying a PT-only storefront.
en_html = (root / 'en/index.html').read_text(encoding='utf-8')
en_cards = re.findall(r'<article class="en-deal-card" data-radar-id="([^"]+)"[^>]*>(.*?)</article>', en_html, re.S)
expected = min(6, sum(bool(radar_source['byId'].get(pid, {}).get('affiliateUrl')) and bool(radar_source['byId'].get(pid, {}).get('imageUrl')) for pid in radar_source.get('featured', [])[:6]))
assert len(en_cards) == expected, f'EN: expected {expected} observed cards, found {len(en_cards)}'
for product_id, body in en_cards:
    product = radar_source['byId'][product_id]
    assert 'Check at retailer' in body and product['affiliateUrl'] in unescape(body)
    assert product['currentPriceText'] in unescape(body)
for guide in ('laptop-buying-guide', 'monitor-buying-guide', 'gaming-setup'):
    assert f'/en/blog/{guide}/' in en_html
    assert (root / 'en' / 'blog' / guide / 'index.html').exists()
print('OK: English observed-price cards and three full guides')
