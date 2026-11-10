#!/usr/bin/env python3
"""MiraDesconto: descoberta Shopee + Mercado Livre, normalização e publicação em GitHub Pages.

Fontes:
* Shopee Affiliate GraphQL productOfferV2 (links afiliados oficiais)
* Mercado Livre /sites/MLB/search + Bot do Afiliado /api/v1/product, quando liberados
* Fallback Mercado Livre: Radar já verificado + links individuais cadastrados (NÃO converte links)
Nunca cria URL afiliada fictícia. Em falhas preserva apenas entradas antes comprovadas.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from urllib.parse import urlsplit

import requests
from dotenv import load_dotenv
from github import Auth, Github, GithubException

ROOT = Path(__file__).resolve().parents[2]
SHOPEE_URL = "https://open-api.affiliate.shopee.com.br/graphql"
ML_SEARCH = "https://api.mercadolibre.com/sites/MLB/search"
BOT_URL_DEFAULT = "https://botdoafiliado.com/api/v1/product"
BLOCKED = {"https://meli.la/1NguveN", "https://meli.la/1pyBZm8"}
TECH = ("notebook", "ssd", "ram", "ryzen", "intel", "core i", "rtx", "placa de video",
        "monitor", "headset", "fone", "mouse", "teclado", "smartphone", "celular",
        "iphone", "tablet", "câmera", "camera", "roteador", "usb", "hdmi",
        "smartwatch", "controle", "bluetooth", "impressora", "drone", "pc gamer")
# Excluir vestuário/bolsas encontrados como falso positivo na busca por "notebook".
NOT_TECH = ("mochila", "bolsa", "pochete", "roupa", "camiseta",
            "calça", "tenis esportivo", "sapato", "mala de viagem")
QUERIES = ("notebook", "ssd nvme", "monitor gamer", "fone bluetooth", "mouse gamer")
LOG = logging.getLogger("minerador")
FIELDS = ("titulo", "preco_atual", "imagem", "link_afiliado", "loja")


def https(value):
    if not isinstance(value, str):
        return ""
    url = value.strip()
    try:
        p = urlsplit(url)
        host = (p.hostname or "").lower()
        if p.scheme != "https" or not host or p.username or p.password or len(url) > 3000:
            return ""
        if host in ("localhost", "127.0.0.1") or host.endswith(".local"):
            return ""
        return url
    except ValueError:
        return ""


def price(value):
    if value is None or isinstance(value, bool):
        return None
    text = str(value).replace("R$", "").replace("\u00a0", "").replace(" ", "").strip()
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        d = Decimal(text)
        return float(d.quantize(Decimal(".01"), rounding=ROUND_HALF_UP)) if d.is_finite() and 0 < d < 1000000 else None
    except (InvalidOperation, ValueError):
        return None


def normalize(title, amount, image, link, loja):
    title = str(title or "").strip()
    amount = price(amount)
    image, link = https(image), https(link)
    if loja not in ("Shopee", "Mercado Livre") or not title or amount is None or not image or not link or link in BLOCKED:
        return None
    if loja == "Mercado Livre" and link.startswith("https://www.mercadolivre.com.br/"):
        if "matt_tool_id=" not in link:
            return None  # Não confundir link normal com link de afiliado.
    return dict(zip(FIELDS, (title[:220], amount, image, link, loja)))


def api_json(response, label):
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError(f"{label}: resposta inesperada")
    return data


def shopee_request(session, app_id, secret, query):
    """Até 2 tentativas para erros transitórios 10000/10030, com nova assinatura."""
    body = json.dumps({"query": query}, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    for attempt in range(2):
        ts = str(int(time.time()))
        sign = hashlib.sha256(app_id.encode() + ts.encode() + body + secret.encode()).hexdigest()
        headers = {"Content-Type": "application/json",
                   "Authorization": f"SHA256 Credential={app_id}, Timestamp={ts}, Signature={sign}"}
        try:
            payload = api_json(session.post(SHOPEE_URL, data=body, headers=headers, timeout=25), "Shopee")
        except requests.RequestException:
            if attempt == 0:
                time.sleep(2)
                continue
            raise
        errors = payload.get("errors") or []
        if errors:
            codes = [str((e.get("extensions") or {}).get("code", "?"))
                     for e in errors if isinstance(e, dict)]
            if attempt == 0 and any(c in ("10000", "10030") for c in codes):
                time.sleep(2)
                continue
            raise ValueError("Shopee GraphQL retornou erro: " + ",".join(codes))
        return payload.get("data") or {}
    raise ValueError("Shopee: falha após tentativas")


def mine_shopee(session, keywords):
    app_id, secret = os.getenv("SHOPEE_APP_ID", ""), os.getenv("SHOPEE_APP_SECRET", "")
    if not (app_id and secret):
        LOG.warning("Shopee sem credenciais; mantém ofertas Shopee anteriormente publicadas")
        return [], False
    rows, success = [], 0
    for keyword in keywords:
        gql = ('query { productOfferV2(keyword: %s, listType: 2, sortType: 2, page: 1, limit: 12)'
               ' { nodes { itemId shopId productName productLink offerLink imageUrl priceMin'
               ' priceMax sales periodEndTime } } }') % json.dumps(keyword)
        try:
            data = shopee_request(session, app_id, secret, gql)
            nodes = (data.get("productOfferV2") or {}).get("nodes")
            if not isinstance(nodes, list):
                raise ValueError("productOfferV2.nodes ausente")
            success += 1
            for n in nodes:
                if not isinstance(n, dict):
                    continue
                try:
                    if n.get("periodEndTime") and int(n["periodEndTime"]) < int(time.time()):
                        continue
                except (ValueError, TypeError):
                    continue
                name = n.get("productName") or ""
                if not is_tech(name):
                    continue
                # offerLink é retornado com tracking pela API; jamais usar productLink no lugar.
                row = normalize(name, n.get("priceMin"), n.get("imageUrl"), n.get("offerLink"), "Shopee")
                if row:
                    rows.append(row)
            LOG.info("Shopee [%s]: %s candidatos", keyword, len(nodes))
        except (requests.RequestException, ValueError) as e:
            LOG.warning("Shopee [%s]: %s", keyword, str(e)[:140] if isinstance(e, ValueError) else type(e).__name__)
    return rows, success == len(keywords)


def is_tech(title):
    name = str(title or "").lower()
    return not any(term in name for term in NOT_TECH) and any(term in name for term in TECH)


def mine_ml_bot(session, keywords):
    key = os.getenv("BOT_API_KEY", "")
    if not key:
        LOG.info("Bot do Afiliado não configurado. Usando Radar verificado existente.")
        return [], False
    endpoint = os.getenv("BOT_PRODUCT_URL", BOT_URL_DEFAULT)
    if not endpoint.startswith("https://botdoafiliado.com/api/v1/"):
        raise ValueError("BOT_PRODUCT_URL deve pertencer à API oficial do Bot do Afiliado")
    found = []
    failed = False
    token = os.getenv("MERCADOLIVRE_ACCESS_TOKEN", "") or os.getenv("ACCESS_TOKEN", "")
    for keyword in keywords[:3]:
        try:
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            data = api_json(session.get(ML_SEARCH, params={"q": keyword, "limit": 12},
                                        headers=headers, timeout=20), "ML")
            results = data.get("results")
            if not isinstance(results, list):
                raise ValueError("ML search sem results")
            found += results
        except (requests.RequestException, ValueError):
            LOG.warning("Busca oficial ML [%s] indisponível; Radar local continuará operando", keyword)
            failed = True
    rows, seen = [], set()
    for p in found[:35]:
        if not isinstance(p, dict) or not is_tech(p.get("title", "")):
            continue
        url = https(p.get("permalink"))
        if not url or url in seen or not (urlsplit(url).hostname or "").endswith("mercadolivre.com.br"):
            continue
        seen.add(url)
        try:
            converted = api_json(session.post(endpoint, json={"url": url},
                headers={"X-API-Key": key, "Content-Type": "application/json"}, timeout=30), "Bot")
            if converted.get("success") is False:
                continue
            d = converted.get("data") if isinstance(converted.get("data"), dict) else converted
            obj = d.get("product") if isinstance(d.get("product"), dict) else d
            link = d.get("final_url") or d.get("affiliate_url") or obj.get("final_url") or obj.get("affiliate_url")
            if not link or link.rstrip("/") == url.rstrip("/"):
                continue
            row = normalize(obj.get("title") or obj.get("name") or p.get("title"),
                            obj.get("price") or obj.get("current_price"),
                            obj.get("image_url") or obj.get("image") or p.get("thumbnail"),
                            link, "Mercado Livre")
            if row:
                rows.append(row)
        except (requests.RequestException, ValueError):
            failed = True
    return rows, not failed


def verified_radar(now=None):
    """Reaproveita SOMENTE links individuais e preços recentes gerados pelo próprio site."""
    now = now or datetime.now(timezone.utc)
    try:
        radar = json.loads((ROOT / "_data/radar.json").read_text(encoding="utf-8"))
        registry = json.loads((ROOT / "_data/produtos.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        LOG.warning("Radar indisponível: %s", type(exc).__name__)
        return []
    by_id = radar.get("byId") or {}
    ordered = list(dict.fromkeys([*(radar.get("featured") or []), *by_id.keys()]))
    rows = []
    for item_id in ordered:
        p, reg = by_id.get(item_id, {}), registry.get(item_id, {})
        if not isinstance(p, dict) or not isinstance(reg, dict):
            continue
        if reg.get("available") is False or not is_tech(p.get("name") or ""):
            continue
        checked_at = p.get("checkedAt")
        try:
            when = datetime.fromisoformat(str(checked_at).replace("Z", "+00:00"))
            age = (now - when).total_seconds()
            if age < 0 or age > 36 * 3600:
                continue
        except (ValueError, TypeError):
            continue
        link = reg.get("affiliateUrl") or p.get("affiliateUrl")
        row = normalize(p.get("name"), p.get("currentPrice"), p.get("imageUrl"), link, "Mercado Livre")
        if row:
            rows.append(row)
    return rows[:30]


def previous_items(path):
    try:
        old = json.loads(path.read_text(encoding="utf-8"))
        return [normalized for p in old if isinstance(p, dict) and
                (normalized := normalize(*(p.get(k) for k in FIELDS))) is not None and is_tech(normalized["titulo"])]
    except (OSError, ValueError, TypeError):
        return []


def merge_items(shopee, ml, old, *, shopee_ok, ml_ok, limit=36):
    # Falhas não apagam links aprovados em execução anterior.
    # Uma palavra-chave pode falhar mesmo com outras respostas autênticas.
    # Publicar os resultados válidos da consulta parcial, sem descartar tudo.
    if not shopee_ok and not shopee:
        shopee = [r for r in old if r["loja"] == "Shopee"]
    if not ml_ok and not ml:
        ml = [r for r in old if r["loja"] == "Mercado Livre"]
    unique = {}
    # Intercalar lojas para a vitrine não exibir somente um marketplace.
    for i in range(max(len(shopee), len(ml))):
        for group in (shopee, ml):
            if i < len(group):
                row = group[i]
                unique.setdefault(row["loja"] + ":" + row["link_afiliado"], row)
    return list(unique.values())[:limit]


def commit_github(path, content):
    from github import Auth, Github, GithubException
    token = os.getenv("GITHUB_TOKEN", "")
    repo_name = os.getenv("GITHUB_REPO", "miradesconto/miradesconto")
    if not token:
        raise RuntimeError("GITHUB_TOKEN ausente")
    gh = Github(auth=Auth.Token(token))
    try:
        repo = gh.get_repo(repo_name)
        for attempt in range(3):
            try:
                old = repo.get_contents(path, ref="main")
                if old.decoded_content.decode("utf-8") == content:
                    return False
                repo.update_file(path, "chore: atualizar mineração de ofertas", content, old.sha, branch="main")
                return True
            except GithubException as e:
                if e.status == 404:
                    repo.create_file(path, "feat: iniciar feed de ofertas", content, branch="main")
                    return True
                if e.status in (409, 422) and attempt < 2:
                    time.sleep(attempt + 1)
                    continue
                raise
    finally:
        gh.close()
    return False


def trigger_pages(session):
    token = os.getenv("GITHUB_TOKEN", "")
    repo_name = os.getenv("GITHUB_REPO", "miradesconto/miradesconto")
    response = session.post(f"https://api.github.com/repos/{repo_name}/pages/builds",
        json={}, headers={"Authorization": f"Bearer {token}",
                          "Accept": "application/vnd.github+json"}, timeout=25)
    response.raise_for_status()


def run(*, publish=False, output=ROOT / "api/produtos.json"):
    load_dotenv(ROOT / ".env")
    keywords = tuple(x.strip() for x in os.getenv("MINERAR_KEYWORDS", ",".join(QUERIES)).split(",") if x.strip())[:8]
    if not keywords:
        raise ValueError("MINERAR_KEYWORDS vazio")
    old = previous_items(output)
    with requests.Session() as s:
        s.headers["User-Agent"] = "MiraDesconto/1.0 (+https://miradesconto.com.br)"
        shopee, shopee_ok = mine_shopee(s, keywords)
        bot, bot_ok = mine_ml_bot(s, keywords)
        radar = verified_radar()
        ml = bot + radar
        ml_ok = bool(bot or radar) and (bot_ok or bool(radar))
        items = merge_items(shopee, ml, old, shopee_ok=shopee_ok, ml_ok=ml_ok)
        if not items:
            LOG.error("Nenhum link válido: feed anterior preservado")
            return 2
        content = json.dumps(items, ensure_ascii=False, indent=2) + "\n"
        output.parent.mkdir(parents=True, exist_ok=True)
        changed = not output.exists() or output.read_text(encoding="utf-8") != content
        output.write_text(content, encoding="utf-8")
        LOG.info("Ofertas: %d (Shopee novas=%d, Bot=%d, Radar=%d, alterado=%s)",
                 len(items), len(shopee), len(bot), len(radar), changed)
        if publish:
            uploaded = commit_github("api/produtos.json", content)
            LOG.info("GitHub atualizado=%s", uploaded)
            if uploaded:
                trigger_pages(s)
        return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--publish", action="store_true", help="Commit via PyGithub + solicitar rebuild Pages")
    parser.add_argument("--output", type=Path, default=ROOT / "api/produtos.json")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        sys.exit(run(publish=args.publish, output=args.output))
    except (RuntimeError, requests.RequestException, GithubException, ValueError) as exc:
        LOG.error("Falha no minerador: %s", type(exc).__name__)
        sys.exit(1)
