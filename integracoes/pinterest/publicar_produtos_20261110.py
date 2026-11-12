"""Lote único de cinco Pins originais do catálogo, com reconciliação e persistência."""
import hashlib
import io
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
from collections import deque

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
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

def load_source(post):
    """Usa a fotografia real do anúncio; não substitui o produto por imagem inventada."""
    if post.get("image"):
        local = (ROOT / post["image"]).resolve()
        if not local.is_relative_to((ROOT / "assets/ofertas").resolve()) or not local.is_file():
            raise ValueError("Foto local fora do catálogo")
        raw = local.read_bytes()
    else:
        url = post.get("imageUrl", "")
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname != "http2.mlstatic.com":
            raise ValueError("Origem de foto não autorizada")
        request = Request(url, headers={"User-Agent": "Mozilla/5.0 (MiraDesconto/1.0)"})
        with urlopen(request, timeout=25) as response:
            if response.status != 200:
                raise RuntimeError("Foto do produto indisponível")
            raw = response.read(6_000_001)
        if len(raw) > 6_000_000:
            raise ValueError("Foto excedeu tamanho máximo")
    with Image.open(io.BytesIO(raw)) as loaded:
        original = ImageOps.exif_transpose(loaded).convert("RGB")
        if min(original.size) < 200:
            raise ValueError("Foto de produto muito pequena")
        return original.copy()


def studio_background():
    """Fundo fotográfico neutro, sem textos nem cartões promocionais."""
    canvas = Image.new("RGBA", (1000, 1500))
    px = canvas.load()
    for y in range(1500):
        t = y / 1499
        base = (int(244 - 19*t), int(246 - 13*t), int(241 - 16*t), 255)
        for x in range(1000):
            px[x, y] = base
    glow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(glow)
    d.ellipse((-420, -230, 710, 990), fill=(255, 255, 249, 170))
    d.ellipse((610, 380, 1500, 1510), fill=(176, 199, 184, 135))
    glow = glow.filter(ImageFilter.GaussianBlur(115))
    canvas = Image.alpha_composite(canvas, glow)
    d = ImageDraw.Draw(canvas)
    d.line((0, 1180, 1000, 1180), fill=(222, 226, 215, 120), width=3)
    return canvas


def edge_background_mask(photo):
    """Recorta somente o branco conectado às bordas, preservando detalhes internos claros."""
    w, h = photo.size
    pix = photo.load()
    mask = Image.new("L", (w, h), 255)
    mp = mask.load()
    seen = bytearray(w * h)
    q = deque()
    def white(x, y):
        r, g, b = pix[x, y]
        return min(r, g, b) >= 237 and max(r, g, b) - min(r, g, b) <= 25
    for x in range(w):
        if white(x, 0):
            q.append((x, 0))
        if white(x, h-1):
            q.append((x, h-1))
    for y in range(h):
        if white(0, y):
            q.append((0, y))
        if white(w-1, y):
            q.append((w-1, y))
    count = 0
    while q:
        x, y = q.popleft()
        i = y*w+x
        if seen[i]:
            continue
        seen[i] = 1
        if not white(x, y):
            continue
        mp[x,y] = 0
        count += 1
        if x:
            q.append((x-1,y))
        if x < w-1:
            q.append((x+1,y))
        if y:
            q.append((x,y-1))
        if y < h-1:
            q.append((x,y+1))
    if count < (w*h)*0.06:
        return None
    return mask.filter(ImageFilter.GaussianBlur(1.2))


def make_art(post):
    """Pin 1000×1500: fotografia fiel ao anúncio, estética de estúdio, sem card textual."""
    original = load_source(post)
    # Fotos em cenário real são preservadas em tela cheia, sem sobreposição de texto.
    corners = [original.getpixel((x,y))
               for x,y in ((0,0),(original.width-1,0),(0,original.height-1),
                           (original.width-1,original.height-1))]
    plain = sum(1 for c in corners if min(c)>230 and max(c)-min(c)<30) >= 3
    if not plain:
        hero = ImageOps.fit(original, (1000,1500), method=Image.Resampling.LANCZOS,
                            centering=(0.5,0.5))
        out = io.BytesIO()
        hero.save(out, format="JPEG", quality=91, optimize=True)
        return out.getvalue()
    canvas = studio_background()
    source = ImageOps.contain(original, (1080,1080), method=Image.Resampling.LANCZOS)
    mask = edge_background_mask(source)
    if mask is None:
        # Não fabricar recorte caso a imagem não tenha fundo branco confiável.
        hero = ImageOps.contain(original, (910,1050), method=Image.Resampling.LANCZOS)
        mask = Image.new("L", hero.size, 255)
        mask = mask.filter(ImageFilter.GaussianBlur(2))
    else:
        box = mask.getbbox()
        if not box:
            raise ValueError("Foto sem produto reconhecível")
        source = source.crop(box)
        mask = mask.crop(box)
        hero = ImageOps.contain(source, (895,1020), method=Image.Resampling.LANCZOS)
        mask = mask.resize(hero.size, Image.Resampling.LANCZOS)
    x = (1000-hero.width)//2
    y = 285 + (920-hero.height)//2
    # Sombra difusa + contato com a superfície, para aspecto de estúdio.
    shadow_alpha = mask.filter(ImageFilter.GaussianBlur(28)).point(lambda n: int(n*0.32))
    shadow = Image.new("RGBA", hero.size, (30,49,36,0))
    shadow.putalpha(shadow_alpha)
    canvas.alpha_composite(shadow, (x+16, y+31))
    product = hero.convert("RGBA")
    product.putalpha(mask)
    canvas.alpha_composite(product, (x,y))
    finished = canvas.convert("RGB")
    out=io.BytesIO()
    finished.save(out, format="JPEG", quality=90, optimize=True)
    return out.getvalue()

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
          "description":p.get("description", p["subtitle"])+ " Publicidade: link de afiliado; podemos receber comissão em compras elegíveis. Confira preço e disponibilidade na loja.",
          "link":p["link"],"alt_text":"Fotografia de produto: "+p["title"],
          "media_source":{"source_type":"image_base64","content_type":"image/jpeg",
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
