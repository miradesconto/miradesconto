"""Validate actual Jekyll output, including links, canonicals and JSON-LD."""
import json
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
from xml.etree import ElementTree

root=Path(sys.argv[1] if len(sys.argv)>1 else '_site')
base='/miradesconto'
origin='https://miradesconto.github.io'
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
