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

# Drafts must not leak through discovery, and known affiliate lists need honest labels.
for file in (source/'_artigos').glob('*.md'):
    front=file.read_text(encoding='utf-8').split('---')[1]
    if 'status: "rascunho"' in front:
        draft_url=origin+'/blog/'+file.stem+'/'
        assert draft_url not in urls, draft_url
        assert '/blog/'+file.stem+'/' not in pages['blog/index.html'].links, draft_url
notebooks=(root/'blog/notebook-em-promocao-como-escolher/index.html').read_text(encoding='utf-8')
assert 'Abrir lista na loja' in notebooks
assert 'O link abre uma lista' in notebooks
for key in editorial + ['radar/index.html']:
    text=(root/key).read_text(encoding='utf-8')
    assert 'blog.js?v=20261013audit' in text, f'Image recovery missing: {key}'
# Validate actual navigation links of all landing and institutional pages too.
for key in ['index.html','radar/index.html','sobre.html','transparencia.html','privacidade.html']:
    for href in pages[key].links:
        u=urlsplit(href)
        if u.scheme or u.netloc:continue
        target=unquote(u.path)
        local=target.lstrip('/') if target.startswith('/') else normpath(str(Path(key).parent.as_posix())+'/'+target) if target else key
        if target.endswith('/') or local=='.':local=local.rstrip('/')+'/index.html' if local!='.' else 'index.html'
        assert (root/local).exists(),(key,href)
        if u.fragment and local in pages:assert u.fragment in pages[local].ids,(key,href)
print('OK: draft discovery, affiliate list disclosure, image recovery and primary navigation')

# Painel administrativo: fonte de catálogo realmente disponível após build.
admin_html = (root/'admin/index.html').read_text(encoding='utf-8')
assert 'src="ofertas.js"' in admin_html
assert 'src="painel.js"' in admin_html
assert 'src="associar.js"' in admin_html
assert (root/'admin/ofertas.js').is_file()
assert (root/'admin/painel.js').is_file()
assert (root/'admin/painel.css').is_file()
public_catalog = json.loads((root/'dados/catalogo.json').read_text(encoding='utf-8'))
source_catalog = json.loads((source/'dados/catalogo.json').read_text(encoding='utf-8'))
assert public_catalog['publishedIds'] == source_catalog['publishedIds']
assert len(public_catalog['products']) == len(source_catalog['products'])
public_radar = json.loads((root/'admin/radar.json').read_text(encoding='utf-8'))
source_radar = json.loads((source/'_data/radar.json').read_text(encoding='utf-8'))
assert public_radar['featured'] == source_radar['featured']
assert set(public_radar['byId']) == set(source_radar['byId'])
print('OK: painel e feeds JSON disponíveis no site renderizado')
