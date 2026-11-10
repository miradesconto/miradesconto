"""Diagnostic: confirm if Shopee/ML product images are fetchable from CI.
Only checks existing marketplace URLs, no credentials, no writes.
"""
import json
import requests
from pathlib import Path
from urllib.parse import urlsplit
from concurrent.futures import ThreadPoolExecutor

root=Path(__file__).resolve().parents[1]
items=json.loads((root/"api/produtos.json").read_text(encoding="utf-8"))
cases=[]
for loja in ("Shopee","Mercado Livre"):
    found=[i for i in items if i["loja"]==loja][:3]
    for i in found:
        origin=i["imagem"]
        cases.append((loja,"original",origin))
        if loja=="Shopee" and origin.startswith("https://cf.shopee.com.br/file/"):
            cases.append((loja,"down-br",origin.replace("https://cf.shopee.com.br/file/","https://down-br.img.susercontent.com/file/")))
            cases.append((loja,"down-bs-br",origin.replace("https://cf.shopee.com.br/file/","https://down-bs-br.img.susercontent.com/file/")))

def probe(t):
    store,label,url=t
    try:
        response=requests.get(url,timeout=9,headers={"User-Agent":"Mozilla/5.0 (compatible; MiraDescontoImageCheck/1.0)","Accept":"image/avif,image/webp,image/apng,image/*,*/*;q=0.8"},stream=True)
        start=next(response.iter_content(32),b"")
        typ=response.headers.get("content-type","")
        magic=start.startswith((b"\xff\xd8\xff",b"\x89PNG",b"RIFF",b"GIF8"))
        return f"{store}: {label}, HTTP {response.status_code}, {typ}, image-magic={magic}, host={urlsplit(url).hostname}"
    except requests.RequestException as exc:
        return f"{store}: {label}, {type(exc).__name__}, host={urlsplit(url).hostname}"

with ThreadPoolExecutor(max_workers=7) as pool:
    for msg in pool.map(probe,cases):
        print(msg,flush=True)
