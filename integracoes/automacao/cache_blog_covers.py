#!/usr/bin/env python3
"""Cache real editorial product photos locally; never generate placeholder artwork."""
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
DEST=ROOT/"assets/blog/covers"
ALLOWED={"http2.mlstatic.com", "down-br.img.susercontent.com", "blog.playstation.com"}
MAX_BYTES=8_000_000
covers=json.loads((ROOT/"_data/editorial_covers.json").read_text())
products={}
for name in ("produtos.json","editorial_products.json"):
    products.update(json.loads((ROOT/"_data"/name).read_text()))

def image_valid(path):
    if not path.is_file() or path.stat().st_size<10000:
        return False
    data=path.read_bytes()
    if path.suffix==".png": return data.startswith(b"\x89PNG\r\n\x1a\n")
    if path.suffix in (".jpg",".jpeg"): return data.startswith(b"\xff\xd8") and data.endswith(b"\xff\xd9")
    if path.suffix==".webp": return data[:4]==b"RIFF" and data[8:12]==b"WEBP"
    if path.suffix==".svg": return b"<svg" in data[:1500] and b"</svg>" in data
    return False

def get_image(url):
    p=urllib.parse.urlsplit(url)
    if p.scheme!="https" or p.hostname not in ALLOWED:
        return None
    try:
        req=urllib.request.Request(url,headers={"User-Agent":"MiraDesconto-Editorial/1.0", "Accept":"image/webp,image/jpeg,image/png"})
        with urllib.request.urlopen(req,timeout=16) as r:
            data=r.read(MAX_BYTES+1)
            if len(data)>MAX_BYTES or len(data)<10000: return None
            typ=r.headers.get("content-type","").split(";")[0].lower()
        if data.startswith(b"\xff\xd8") and data.endswith(b"\xff\xd9"): return ".jpg",data
        if data[:4]==b"RIFF" and data[8:12]==b"WEBP": return ".webp",data
        if data.startswith(b"\x89PNG\r\n\x1a\n"): return ".png",data
    except Exception as e:
        print("Falha ao obter imagem:",p.hostname,str(e),file=sys.stderr)
    return None

DEST.mkdir(parents=True,exist_ok=True)
changed=0
missing=[]
for article in sorted((ROOT/"_artigos").glob("*.md")):
    body=article.read_text(encoding="utf-8")
    if not re.search(r'^status:\s*"publicado"\s*$',body,re.M): continue
    slug=article.stem
    field=re.search(r'^(custom_image|cover|image):\s*["\x27]?([^"\x27\n]+)',body,re.M)
    current=field.group(2).strip() if field else ""
    if current.startswith("/assets/") and image_valid(ROOT/current.lstrip("/")):
        continue
    sources=[covers.get(slug,""),current]
    sources += re.findall(r'!\[[^\]]*\]\((https://[^)\s]+)',body)
    match=re.search(r'^produtos:\s*(\[.*\])',body,re.M)
    if match:
        try:
            for pid in json.loads(match.group(1)):
                sources.append(products.get(pid,{}).get("imageUrl",""))
        except (ValueError,TypeError): pass
    selected=None
    for source in sources:
        if not source: continue
        if source.startswith("/assets/") and image_valid(ROOT/source.lstrip("/")):
            selected=source
            break
        if source.startswith("https://"):
            result=get_image(source)
            if result:
                ext,data=result
                path=DEST/(slug+ext)
                path.write_bytes(data)
                selected="/"+path.relative_to(ROOT).as_posix()
                break
    if not selected:
        missing.append(slug)
        print("SEM CAPA VERIFICADA:",slug)
        continue
    if re.search(r'^custom_image:',body,re.M):
        body=re.sub(r'^custom_image:.*$',"custom_image: "+json.dumps(selected),body,count=1,flags=re.M)
    else:
        body=body.replace("---\n","---\ncustom_image: "+json.dumps(selected)+"\n",1)
    article.write_text(body,encoding="utf-8")
    changed+=1
    print("CAPA REAL:",slug,selected)
print("Imagens corrigidas:",changed,"Artigos ainda sem foto:",len(missing))
if missing:
    print("PENDENTES:",", ".join(missing))
