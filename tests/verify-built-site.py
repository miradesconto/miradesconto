"""Validate actual Jekyll output, including links, canonicals and JSON-LD."""
import json
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


# Radar ↔ Blog regression checks: only published articles matching the exact listing ID.
class RadarConversionAudit(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.cards = []
        self.active = False
        self.link = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'article' and 'radar-card' in attrs.get('class', '').split():
            assert not self.active, 'Unexpected nested Radar card'
            self.cards.append([])
            self.active = True
        elif self.active and tag == 'a':
            self.link = dict(attrs)
            self.link['text'] = ''
            self.cards[-1].append(self.link)

    def handle_data(self, data):
        if self.active and self.link is not None:
            self.link['text'] += data

    def handle_endtag(self, tag):
        if tag == 'a':
            self.link = None
        elif tag == 'article' and self.active:
            self.active = False


radar_data = json.loads((source/'_data/radar.json').read_text(encoding='utf-8'))
radar_cards = RadarConversionAudit((root/'radar/index.html').read_text(encoding='utf-8')).cards
assert len(radar_cards) == len(radar_data['featured']), 'Radar cards and highlighted item IDs differ'

published_by_id = {}
for article_file in (source/'_artigos').glob('*.md'):
    front = article_file.read_text(encoding='utf-8').split('---', 2)[1]
    if 'status: "publicado"' not in front:
        continue
    products_line = next((line for line in front.splitlines() if line.startswith('produtos: ')), None)
    product_ids = json.loads(products_line.split(': ', 1)[1]) if products_line else []
    for product_id in product_ids:
        published_by_id.setdefault(product_id, set()).add('/blog/'+article_file.stem+'/')

editorial_links = 0
for item_id, links in zip(radar_data['featured'], radar_cards):
    data = radar_data['byId'][item_id]
    primary = [link for link in links if 'radar-primary' in link.get('class', '').split()]
    assert len(primary) == 1, f'Expected exactly one primary offer CTA for {item_id}'
    primary = primary[0]
    assert primary.get('href') == data['affiliateUrl'], f'Primary CTA target changed for {item_id}'
    assert primary.get('data-item-id') == item_id, f'Primary CTA tracking ID mismatch: {item_id}'
    assert primary.get('data-link-location') == 'radar'
    assert primary.get('target') == '_blank'
    assert {'sponsored', 'nofollow', 'noopener', 'noreferrer'} <= set(primary.get('rel', '').split())
    assert primary['text'].strip() == 'VER OFERTA NA LOJA ↗', f'CTA label incorrect: {item_id}'

    related = [link for link in links if link['text'].strip() == 'Ler análise de compra →']
    allowed = published_by_id.get(item_id, set())
    assert len(related) == (1 if allowed else 0), f'Unwanted or missing article link for {item_id}'
    if allowed:
        assert related[0].get('href') in allowed, f'Article is not about this listing: {item_id}'
        local = related[0]['href'].lstrip('/')+'index.html'
        assert (root/local).is_file(), f'Broken article link: {item_id}'
        editorial_links += 1
print(f'OK: {len(radar_cards)} Radar cards, exact affiliate CTAs and {editorial_links} published article links')
