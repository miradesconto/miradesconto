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

# Shared public navigation, generated feeds and published-only product/article links.
for key in ['index.html','radar/index.html','sobre.html','privacidade.html','transparencia.html'] + editorial:
    text=(root/key).read_text(encoding='utf-8')
    assert '/site.css?v=' in text,key
    assert 'Navegação principal' in text,key
    assert 'Informações institucionais' in text,key
    p=pages[key]
    for destination in ['/radar/','/blog/','/sobre.html','/transparencia.html','/privacidade.html']:
        assert destination in p.links,(key,destination)
manifest=json.loads((root/'catalogo/feed.json').read_text())
assert manifest['files']
for file in manifest['files']:
    assert file.startswith('/catalogo/produtos-') and (root/file.lstrip('/')).exists(),file
    assert isinstance(json.loads((root/file.lstrip('/')).read_text()),list),file
radar=json.loads((root/'radar/feed.json').read_text())
assert radar['methodology']['maxPriceAgeHours']==2
assert len(radar['featured']) <= 12
class InlineData(HTMLParser):
    def __init__(self,text):
        super().__init__();self.active=False;self.buffer='';self.value=None;self.feed(text)
    def handle_starttag(self,tag,attrs):
        if tag=='script' and dict(attrs).get('id')=='editorial-data':self.active=True
    def handle_data(self,data):
        if self.active:self.buffer+=data
    def handle_endtag(self,tag):
        if tag=='script' and self.active:self.value=json.loads(self.buffer);self.active=False
mapping=InlineData((root/'index.html').read_text()).value
assert mapping and len(mapping)==len(editorial)-1
for entry in mapping:
    assert entry['url'].startswith('/blog/') and (root/entry['url'].lstrip('/')/'index.html').exists()
print('OK: shared navigation, catalog/Radar feeds, and published-only editorial mapping')
