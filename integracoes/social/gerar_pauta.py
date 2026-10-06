#!/usr/bin/env python3
from __future__ import annotations
import json, math, re, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "integracoes"))
from qualidade import usable_price
from tech_policy import eligible as tech_eligible

CATALOG = ROOT / "produtos.js"
RADAR = ROOT / "_data" / "radar.json"
ARTIGOS = ROOT / "_artigos"
OUT_JSON = Path(__file__).with_name("pauta-do-dia.json")
OUT_MD = Path(__file__).with_name("pauta-do-dia.md")
SITE = "https://miradesconto.github.io/miradesconto"
MAX_POSTS, MAX_CAT = 14, 2

GEMINI_PROMPT = (
    "Revise a fila de vídeos do MiraDesconto. Aponte apenas afirmações sem evidência, "
    "preço/histórico incoerente, linguagem que pareça teste físico sem teste, promessa exagerada, "
    "CTA confuso ou roteiro longo demais para 20-25s. Nunca trate referência da loja como histórico. "
    "Preserve números do Radar, links e identidade. Se estiver tudo correto, diga que pode seguir para o Pippit."
)

def load_catalog():
    text = CATALOG.read_text(encoding="utf-8")
    m = re.search(r"window\.MIRA_DATA\s*=\s*(\{.*\})\s*;?\s*$", text, re.S)
    if not m: raise RuntimeError("Não foi possível ler produtos.js")
    return json.loads(m.group(1))

def load_radar():
    return json.loads(RADAR.read_text(encoding="utf-8"))

def articles():
    out = []
    for p in ARTIGOS.glob("*.md"):
        text = p.read_text(encoding="utf-8")
        if not text.startswith("---"): continue
        f = text.split("---", 2)[1]
        if not re.search(r"^status:\s*[\"']?publicado", f, re.M): continue
        m = re.search(r"^produtos:\s*\[(.*?)\]\s*$", f, re.M)
        if not m: continue
        ids = re.findall(r"MLB\d+", m.group(1))
        t = re.search(r"^title:\s*[\"']?(.*?)[\"']?\s*$", f, re.M)
        out.append({"ids": ids, "title": (t.group(1).strip('"\'') if t else p.stem), "url": f"{SITE}/blog/{p.stem}/"})
    return out

def num(v, d=0.0):
    try: return float(v)
    except (TypeError, ValueError): return d

def eligible(p):
    return (
        bool(p.get("name")) and num(p.get("price")) > 0
        and p.get("available") is True
        and str(p.get("availabilityStatus") or "") == "available"
        and str(p.get("affiliateUrl") or "").startswith("https://meli.la/")
        and str(p.get("imageUrl") or "").startswith("http")
        and tech_eligible(p) and usable_price(p)
    )

def ok(p, radar):
    return str(p.get("id") or "") in (radar.get("byId") or {}) and eligible(p)

def article_for(i, arts):
    m = [a for a in arts if i in a["ids"]]
    return sorted(m, key=lambda a: len(a["ids"]))[0] if m else None

def score(p, radar, arts):
    i, r = str(p["id"]), radar["byId"][str(p["id"])]
    featured = radar.get("featured") or []
    s = 55 if r.get("actionable") else 0
    s += num(r.get("strength")) * 22 + max(0, -num(r.get("deltaAveragePct"))) * 2.5
    s += min(num(r.get("observations")), 120) * .08 + min(num(r.get("spanDays")), 30) * .6
    if i in featured: s += max(10, 45 - featured.index(i) * 3)
    if article_for(i, arts): s += 12
    return s

def choose(products, radar, arts):
    ranked = sorted([p for p in products if ok(p, radar)], key=lambda p: (-score(p, radar, arts), int(p.get("rank") or 999999)))
    out, cats, seen = [], Counter(), set()
    for p in ranked:
        c = str(p.get("category") or "Outros")
        if cats[c] >= MAX_CAT: continue
        out.append(p); cats[c] += 1; seen.add(str(p["id"]))
        if len(out) == MAX_POSTS: return out
    for p in ranked:
        if str(p["id"]) not in seen:
            out.append(p)
            if len(out) == MAX_POSTS: break
    return out

def short(name):
    name = re.sub(r"\s+", " ", name).strip()
    return name if len(name) <= 72 else name[:68].rsplit(" ", 1)[0] + "…"

def angle(r):
    if r.get("label") == "Menor observado": return "Menor preço observado: vale aproveitar?"
    if r.get("label") == "Bom preço" or num(r.get("deltaAveragePct")) <= -2: return "Abaixo da média observada: vale agora?"
    if r.get("label") == "Preço estável": return "Preço estável: vale pelo conjunto?"
    return "Preço na Mira: vale comprar agora?"

def hook(name, r):
    d = num(r.get("deltaAveragePct"))
    if r.get("label") == "Menor observado":
        return f"{name} está no menor valor observado neste anúncio. Mas vale comprar agora?"
    if d <= -2: return f"{name} está {abs(d):.1f}% abaixo da média observada. É um bom momento de compra?"
    if r.get("label") == "Preço estável": return f"{name} quase não mudou de preço. Então o que decide a compra?"
    return f"Antes de comprar {name}, olha o que o histórico mostra."

def make_entry(p, r, arts, pos):
    name, i = short(str(p["name"])), str(p["id"])
    a = article_for(i, arts)
    dest = {"type": "article", "title": a["title"], "url": a["url"]} if a else {
        "type": "offer", "title": "Ofertas MiraDesconto", "url": f"{SITE}/?produto={i}#ofertas"
    }
    cta = "Veja o guia no MiraDesconto" if a else "Veja no Radar MiraDesconto"
    script = (
        f"{hook(name, r)} Hoje ele aparece por {r.get('currentPriceText')}. "
        f"No Radar, a média foi {r.get('averagePriceText')} e o menor valor observado foi {r.get('minimumPriceText')}, "
        f"em {r.get('periodText')}. {r.get('reason')} {cta} antes de comprar."
    )
    caption = (
        f"PREÇO NA MIRA — {name}\nHoje: {r.get('currentPriceText')}\nMédia observada: {r.get('averagePriceText')}\n"
        f"Menor observado: {r.get('minimumPriceText')}\nBase: {r.get('periodText')}\n\n{r.get('reason')}\n\n"
        f"{cta}: {dest['url']}\nPreço pode mudar. Link comercial pode gerar comissão sem custo adicional."
    )
    prompt = (
        "Vídeo vertical 9:16, 20-25s, MiraDesconto. Use somente a imagem oficial e motion graphics; "
        "não simule unboxing, teste físico ou posse do produto. Cores #101D20 #86EFAC #F8FAFC #A8B8B3. "
        f"Narração pt-BR natural e nítida. Produto: {name}. Imagem: {p.get('imageUrl')}. "
        f"Hook 0-3s: {hook(name, r)} Mostre preço atual {r.get('currentPriceText')}, média {r.get('averagePriceText')} "
        f"e menor observado {r.get('minimumPriceText')}. Narração: {script} CTA: {cta}. "
        "Não use desconto da loja como histórico; texto grande e cortes rápidos."
    )
    return {
        "position": pos, "day": math.ceil(pos / 2), "slot": 1 if pos % 2 else 2, "status": "ready_for_pippit",
        "id": i, "name": name, "fullName": p.get("name"), "category": p.get("category"),
        "imageUrl": p.get("imageUrl"), "affiliateUrl": p.get("affiliateUrl"), "angle": angle(r), "hook": hook(name, r),
        "currentPriceText": r.get("currentPriceText"), "averagePriceText": r.get("averagePriceText"),
        "minimumPriceText": r.get("minimumPriceText"), "maximumPriceText": r.get("maximumPriceText"),
        "deltaAveragePct": r.get("deltaAveragePct"), "observations": r.get("observations"), "periodText": r.get("periodText"),
        "radarLabel": r.get("label"), "radarReason": r.get("reason"), "destination": dest,
        "script": script, "caption": caption, "cta": cta, "pippitPrompt": prompt
    }

def markdown(payload):
    lines = [
        "# Fila de conteúdo — MiraDesconto → Pippit", "",
        f"**Radar:** {payload.get('radarGeneratedAt')}", f"**Fila:** {payload['count']} vídeos · 2 por dia · 7 dias", "",
        "Prioridade: Radar real, histórico observado, variedade de categorias e artigo de destino. Não usa referência da loja como histórico.", "",
        "## Revisão no Gemini Pro", "", GEMINI_PROMPT, ""
    ]
    for e in payload["posts"]:
        lines += [
            f"## Dia {e['day']} · Vídeo {e['slot']} — {e['name']}", "",
            f"**Ângulo:** {e['angle']}", f"**Preço:** {e['currentPriceText']} · média {e['averagePriceText']} · mínimo {e['minimumPriceText']}",
            f"**Base:** {e['periodText']} · {e['observations']} observações", f"**Destino:** {e['destination']['url']}",
            f"**Imagem:** {e['imageUrl']}", "", "**Hook**", "", e["hook"], "", "**Roteiro**", "", e["script"], "",
            "**Legenda**", "", e["caption"], "", "**Prompt Pippit**", "", e["pippitPrompt"], "", "---", ""
        ]
    return "\n".join(lines).rstrip() + "\n"

def main():
    cat, rad, arts = load_catalog(), load_radar(), articles()
    selected = choose(cat.get("products", []), rad, arts)
    posts = [make_entry(p, rad["byId"][str(p["id"])], arts, n) for n, p in enumerate(selected, 1)]
    payload = {
        "sourceCollectedAt": cat.get("collectedAt"), "radarGeneratedAt": rad.get("generatedAt"),
        "generatedFrom": "Radar MiraDesconto + catálogo + artigos publicados", "count": len(posts),
        "videosPerDay": 2, "selectionPolicy": "radar-first-observed-price-tech-variety-article-priority",
        "geminiReviewPrompt": GEMINI_PROMPT, "posts": posts
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(markdown(payload), encoding="utf-8")
    print(json.dumps({"social_posts_generated": len(posts), "articles_mapped": sum(p["destination"]["type"] == "article" for p in posts)}, ensure_ascii=False))

if __name__ == "__main__":
    main()
