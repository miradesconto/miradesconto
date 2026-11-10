"""Lote único de cinco Pins originais do catálogo, com reconciliação e persistência."""
import hashlib
import io
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

from PIL import Image, ImageDraw, ImageFont
from api import pinterest_request
from publicar_lote import find_board

ROOT = Path(__file__).resolve().parents[2]
CFG = ROOT / "integracoes/pinterest/lote_produtos_20261110.json"
STATE = ROOT / "integracoes/pinterest/estado_produtos_20261110.json"
BOARD = "Ofertas de Tecnologia e Achadinhos | MiraDesconto"

def norm(url):
    return str(url or "").split("#")[0].split("?")[0].rstrip("/")

def save(state):
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    subprocess.run(["git", "add", "--", str(STATE.relative_to(ROOT))], cwd=ROOT, check=True)
    subprocess.run(["git", "commit", "-m", "Registra verificação da publicação Pinterest"], cwd=ROOT, check=True)
    # Se o push falhar, a chamada POST ao Pinterest não acontecerá.
    subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=ROOT, check=True)

def existing_pins(token):
    links, bookmark, seen = {}, None, set()
    while True:
        qs = {"page_size": 250}
        if bookmark: qs["bookmark"] = bookmark
        page = pinterest_request(token, "/pins?" + urlencode(qs))
        if not isinstance(page, dict) or not isinstance(page.get("items"), list):
            raise RuntimeError("Consulta de duplicatas indisponível: publicar bloqueado.")
        for pin in page["items"]:
            if isinstance(pin, dict) and pin.get("link") and pin.get("id"):
                links[norm(pin["link"])] = str(pin["id"])
        bookmark = page.get("bookmark")
        if not bookmark: return links
        if bookmark in seen: raise RuntimeError("Paginação repetida no Pinterest.")
        seen.add(bookmark)

def font(size, bold=False):
    path = "/usr/share/fonts/truetype/dejavu/DejaVuSans" + ("-Bold" if bold else "") + ".ttf"
    return ImageFont.truetype(path, size)

def lines(draw, text, face, maxwidth):
    words = text.split()
    result, current = [], ""
    for word in words:
        trial = (current + " " + word).strip()
        if draw.textbbox((0,0),trial,font=face)[2] > maxwidth and current:
            result.append(current); current = word
        else: current = trial
    if current: result.append(current)
    return result

def make_art(post):
    p = (ROOT / post["image"]).resolve()
    if not p.is_relative_to((ROOT / "assets/ofertas").resolve()) or not p.is_file():
        raise ValueError("Imagem de produto ausente ou fora do catálogo")
    with Image.open(p) as source:
        product = source.convert("RGB")
    if min(product.size) < 200: raise ValueError("Imagem original pequena")
    canvas = Image.new("RGB",(1000,1500),"#f7faf8")
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((52,47,948,1453),radius=35,fill="#ffffff",outline="#dce9de",width=2)
    draw.rounded_rectangle((90,89,460,147),radius=17,fill="#e6f7e9")
    draw.text((112,101),post["category"].upper(),font=font(25,True),fill="#176a3f")
    y=195
    heading_font=font(59,True)
    heading=lines(draw,post["title"],heading_font,800)
    if len(heading)>3: raise ValueError("Título grande demais para arte")
    for line in heading:
        draw.text((94,y),line,font=heading_font,fill="#142d22");y+=79
    subtitle_font=font(30)
    for line in lines(draw,post["subtitle"],subtitle_font,800):
        draw.text((95,y+10),line,font=subtitle_font,fill="#596d62");y+=44
    photo_top=max(470,y+56); photo_bottom=1210
    draw.rounded_rectangle((95,photo_top,905,photo_bottom),radius=25,fill="#f5f8f6")
    w,h=product.size
    scale=min(745/w,(photo_bottom-photo_top-55)/h)
    product=product.resize((max(1,int(w*scale)),max(1,int(h*scale))),Image.Resampling.LANCZOS)
    x=(1000-product.width)//2
    py=photo_top+(photo_bottom-photo_top-product.height)//2
    canvas.paste(product,(x,py))
    draw.rounded_rectangle((95,1245,905,1401),radius=24,fill="#0b4229")
    draw.text((129,1270),"MiraDesconto",font=font(47,True),fill="#ffffff")
    draw.text((130,1340),"Confira no link do Pin",font=font(24),fill="#c4f2d2")
    buf=io.BytesIO()
    canvas.save(buf,format="PNG",optimize=True)
    return buf.getvalue()

def main():
    if os.getenv("GITHUB_ACTIONS")!="true" or os.getenv("GITHUB_REF")!="refs/heads/main":
        raise RuntimeError("Somente workflow de publicação na main.")
    token=os.getenv("PINTEREST_ACCESS_TOKEN","").strip()
    if not token: raise RuntimeError("Token Pinterest ausente nos Secrets.")
    batch=json.loads(CFG.read_text(encoding="utf-8"))
    posts=batch.get("posts",[])
    if batch.get("schemaVersion")!=1 or batch.get("boardName")!=BOARD or len(posts)!=5:
        raise RuntimeError("Lote não autorizado.")
    if len({p["key"] for p in posts})!=5 or len({norm(p["link"]) for p in posts})!=5:
        raise RuntimeError("Produtos repetidos.")
    for p in posts:
        if not re.fullmatch(r"https://meli\.la/[A-Za-z0-9]+",p["link"]):
            raise RuntimeError("Link fora do domínio afiliado aprovado.")
        if not re.fullmatch(r"[a-z0-9-]+",p["key"]): raise ValueError("Chave inválida.")
        if len(p["title"])>100: raise ValueError("Título excede limite")
    # Prepara todas as artes antes de qualquer POST.
    artworks={p["key"]:make_art(p) for p in posts}
    state=json.loads(STATE.read_text(encoding="utf-8"))
    if state.get("schemaVersion")!=1 or not isinstance(state.get("posts"),dict):
        raise RuntimeError("Estado inválido.")
    if any(v.get("status")=="uncertain" for v in state["posts"].values()):
        raise RuntimeError("Envio anterior incerto; reconciliação manual obrigatória.")
    existing=existing_pins(token)
    board=find_board(token,BOARD)
    for p in posts:
        key=p["key"]
        prior=state["posts"].get(key)
        if prior:
            print("JÁ PROCESSADO",key,prior.get("status"),prior.get("pinId",""),flush=True)
            continue
        pin_id=existing.get(norm(p["link"]))
        if pin_id:
            state["posts"][key]={"status":"existing","pinId":pin_id}
            save(state)
            print("JÁ EXISTE",key,pin_id,flush=True)
            continue
        # Marca estado remoto ANTES de escrever na API: previne reenvio em falhas.
        state["posts"][key]={"status":"uncertain","startedAt":datetime.now(timezone.utc).isoformat(),"link":p["link"]}
        save(state)
        import base64
        result=pinterest_request(token,"/pins",{
          "board_id":board,"title":p["title"],
          "description":p["subtitle"]+". Oferta em loja parceira; link de afiliado. Confira preço e disponibilidade na loja.",
          "link":p["link"],"alt_text":"Arte editorial MiraDesconto: "+p["title"],
          "media_source":{"source_type":"image_base64","content_type":"image/png",
                          "data":base64.b64encode(artworks[key]).decode("ascii"),"is_standard":True}
        })
        pin_id=str(result.get("id","")) if isinstance(result,dict) else ""
        if not pin_id.isdigit(): raise RuntimeError("Resultado incerto; não repetir automaticamente.")
        check=pinterest_request(token,"/pins/"+pin_id)
        if norm(check.get("link"))!=norm(p["link"]) or str(check.get("board_id"))!=board:
            raise RuntimeError("Verificação de Pin falhou; envio incerto.")
        state["posts"][key]={"status":"published","pinId":pin_id,"link":p["link"]}
        save(state)
        existing[norm(p["link"])]=pin_id
        print("PUBLICADO E VERIFICADO",key,"https://www.pinterest.com/pin/"+pin_id+"/",flush=True)

if __name__=="__main__": main()
