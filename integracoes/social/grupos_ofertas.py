#!/usr/bin/env python3
"""Publicador de ofertas MiraDesconto: Telegram oficial + fila manual WhatsApp.

O feed não inclui prova uniforme de preço ao vivo. Por segurança, o texto
NÃO divulga preço/desconto sem essa evidência; o cliente confere no destino.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
FEED = ROOT / "api/produtos.json"
STATE = ROOT / "integracoes/social/estado-ofertas.json"
BLOCKED = {"https://meli.la/1NguveN", "https://meli.la/1pyBZm8"}
TECH = ("gamer", "ssd", "nvme", "headset", "mouse", "teclado", "monitor",
        "rtx", "placa de vídeo", "placa de video", "notebook", "console",
        "xbox", "playstation", "ps5", "fone", "microfone", "usb", "hdmi",
        "suporte", "cadeira", "mesa", "smartwatch", "smart tv", "controle",
        "hub", "webcam", "roteador", "computador", "pc ", "carregador")
PRIORITY = ("gamer", "mouse", "teclado", "headset", "ssd", "nvme",
            "monitor", "console", "xbox", "ps5", "suporte", "usb")
EXCLUDE = ("religioso", "jesus", "mochila", "roupa", "camiseta", "livro",
           "acesso à conta", "conta digital", "sorteio", "réplica")
COOLDOWN = timedelta(days=5)
MAX_DAILY = 3
MAX_FEED_AGE = timedelta(hours=36)


class BotError(RuntimeError):
    pass


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def timestamp(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            raise ValueError("timezone obrigatória")
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError) as exc:
        raise BotError("Timestamp inválido") from exc


def feed_updated_at() -> datetime:
    raw = os.getenv("MIRA_FEED_UPDATED_AT", "")
    if not raw:
        p = subprocess.run(
            ["git", "-C", str(ROOT), "log", "-1", "--format=%cI", "--", "api/produtos.json"],
            text=True, capture_output=True, check=True,
        )
        raw = p.stdout.strip()
    if not raw:
        raise BotError("Não foi possível comprovar a data de atualização do feed")
    return timestamp(raw)


def valid_link(link: object, shop: str) -> bool:
    if not isinstance(link, str) or len(link) > 2800 or link in BLOCKED:
        return False
    try:
        url = urlsplit(link)
    except ValueError:
        return False
    try:
        if url.scheme != "https" or url.username or url.password or url.port is not None:
            return False
    except ValueError:
        return False
    domain = (url.hostname or "").lower()
    if shop == "Shopee":
        return (domain == "s.shopee.com.br" and
                bool(re.fullmatch(r"/[A-Za-z0-9]+/?", url.path)) and
                not url.query and not url.fragment)
    if shop == "Mercado Livre":
        if domain == "meli.la":
            return bool(re.fullmatch(r"/[A-Za-z0-9]+/?", url.path)) and not url.query
        return (domain in ("mercadolivre.com.br", "www.mercadolivre.com.br") and
                bool(re.search(r"(?:^|[?&])matt_tool_id=\d+", url.query)))
    return False


def normalize(row: object) -> dict | None:
    if not isinstance(row, dict):
        return None
    title = re.sub(r"\s+", " ", str(row.get("titulo") or "")).strip()
    shop, link = row.get("loja"), row.get("link_afiliado")
    name = title.casefold()
    price = row.get("preco_atual")
    if not 6 <= len(title) <= 240 or not isinstance(shop, str):
        return None
    if any(x in name for x in EXCLUDE) or not any(x in name for x in TECH):
        return None
    if not valid_link(link, shop):
        return None
    if isinstance(price, bool) or not isinstance(price, (int, float)):
        return None
    if not math.isfinite(price) or not 10 <= price <= 30000:
        return None
    offer_id = hashlib.sha256((shop + "\n" + link).encode()).hexdigest()[:24]
    return {"id": offer_id, "titulo": title, "loja": shop,
            "link": link, "preco_referencia": round(float(price), 2)}


def read_state(path: Path | None = None) -> dict:
    path = path or STATE
    if not path.exists():
        return {"events": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("events"), list):
        raise BotError("Estado inválido; não publicar até corrigir")
    return data


def select_offer(feed: list, state: dict, now: datetime, updated: datetime) -> dict | None:
    age = now - updated
    if not timedelta(0) <= age <= MAX_FEED_AGE:
        raise BotError("Feed sem atualização comprovada nas últimas 36 horas")
    events = state["events"]
    recent = [e for e in events if 0 <= (now - timestamp(e["at"])).total_seconds()
              < timedelta(days=1).total_seconds()]
    if len(recent) >= MAX_DAILY:
        return None
    used = {e["id"] for e in events
            if timedelta(0) <= now - timestamp(e["at"]) < COOLDOWN}
    latest_shop = recent[-1].get("shop") if recent else ""
    candidates, seen = [], set()
    for raw in feed:
        p = normalize(raw)
        if not p or p["id"] in used or p["id"] in seen:
            continue
        seen.add(p["id"])
        name = p["titulo"].casefold()
        score = sum(2 for x in PRIORITY if x in name)
        if p["loja"] == "Shopee" and p["preco_referencia"] <= 250:
            score += 12
        if p["loja"] == "Mercado Livre" and p["preco_referencia"] >= 250:
            score += 10
        if latest_shop and p["loja"] != latest_shop:
            score += 6
        candidates.append((-score, p["preco_referencia"], p["id"], p))
    return min(candidates)[-1] if candidates else None


def build_text(product: dict) -> tuple[str, str]:
    title = product["titulo"][:175]
    link = product["link"]
    shop = product["loja"]
    # O JSON atual não registra uma comprovação uniforme de preço por anúncio.
    # Não insinuar desconto, estoque, frete grátis ou valor confirmado.
    telegram = (
        "<b>OFERTA TECH NA MIRA</b>\n\n"
        f"<b>{html.escape(title)}</b>\n"
        f"Loja: {html.escape(shop)}\n\n"
        "Confira preço, vendedor, frete e condições antes de comprar.\n\n"
        f'<a href="{html.escape(link, quote=True)}">Ver o anúncio</a>\n\n'
        "Publicidade: link de afiliado; podemos receber comissão."
    )
    whatsapp = (
        f"*OFERTA TECH NA MIRA*\n\n*{title}*\n"
        f"Loja: {shop}\n\nConfira preço, vendedor, frete e condições:\n"
        f"{link}\n\n_Link de afiliado: podemos receber comissão._"
    )
    return telegram, whatsapp


def build_reservation(product: dict, when: datetime) -> dict:
    tg, wa = build_text(product)
    rid = hashlib.sha256((product["id"] + when.isoformat()).encode()).hexdigest()[:20]
    return {"ready": True, "id": rid, "product_id": product["id"], "shop": product["loja"],
            "at": when.isoformat(), "telegram": tg, "whatsapp": wa,
            "whatsapp_share": "https://wa.me/?text=" + quote(wa, safe="")}


def choose(now: datetime) -> dict | None:
    data = json.loads(FEED.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise BotError("Formato do feed inesperado")
    return select_offer(data, read_state(), now, feed_updated_at())


def http_json(method: str, payload: dict, token: str, *, send: bool = False) -> dict:
    url = "https://api.telegram.org/bot" + token + "/" + method
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if send else None
    req = Request(url, data=body, headers={"Content-Type": "application/json"},
                  method="POST" if send else "GET")
    try:
        with urlopen(req, timeout=20) as r:
            data = json.loads(r.read(1024 * 128))
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        raise BotError("Telegram indisponível ou recusou a solicitação; não repetir automaticamente") from exc
    if data.get("ok") is not True or not isinstance(data.get("result"), dict):
        raise BotError("Resposta do Telegram inválida; não repetir automaticamente")
    return data["result"]


def config_bot() -> tuple[str, str]:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat = os.getenv("TELEGRAM_CHAT_ID", "@MiraDesconto")
    if not re.fullmatch(r"\d{5,}:[A-Za-z0-9_-]{20,}", token):
        raise BotError("TELEGRAM_BOT_TOKEN ausente ou inválido")
    if not re.fullmatch(r"(?:-100\d+|@[A-Za-z][A-Za-z0-9_]{4,})", chat):
        raise BotError("TELEGRAM_CHAT_ID inválido")
    return token, chat


def preflight() -> None:
    token, chat = config_bot()
    me = http_json("getMe", {}, token)
    if me.get("is_bot") is not True or not isinstance(me.get("id"), int):
        raise BotError("Credencial não corresponde a um bot válido")
    # getChat e getChatMember usam POST JSON para não expor parâmetros em logs.
    channel = http_json("getChat", {"chat_id": chat}, token, send=True)
    if channel.get("type") != "channel":
        raise BotError("O destino Telegram precisa ser um canal")
    member = http_json("getChatMember",
                       {"chat_id": chat, "user_id": me["id"]}, token, send=True)
    if member.get("status") != "administrator" or member.get("can_post_messages") is not True:
        raise BotError("Adicione o bot como administrador com permissão de publicar")


def prepare(output: Path) -> None:
    now = now_utc()
    p = choose(now)
    if p is None:
        output.write_text('{"ready": false}\n', encoding="utf-8")
        print("Nenhum candidato disponível (limite diário, cooldown ou feed vazio).")
        return
    entry = build_reservation(p, now)
    state = read_state()
    state["events"].append({"id": p["id"], "reservation": entry["id"],
                            "shop": p["loja"], "at": entry["at"], "status": "reserved"})
    # Manter registro limitado, preservando eventos recentes para cooldown/antiduplicata.
    state["events"] = [e for e in state["events"]
                       if now - timestamp(e["at"]) < timedelta(days=30)]
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output.write_text(json.dumps(entry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Oferta reservada antes do envio:", entry["id"], p["loja"])


def send(prepared: Path, result_file: Path) -> None:
    info = json.loads(prepared.read_text(encoding="utf-8"))
    if not info.get("ready"):
        raise BotError("Nenhuma reserva pronta para enviar")
    token, chat = config_bot()
    receipt = {"reservation": info["id"], "status": "uncertain"}
    try:
        msg = http_json("sendMessage", {
            "chat_id": chat, "text": info["telegram"], "parse_mode": "HTML",
            "link_preview_options": {"is_disabled": True},
        }, token, send=True)
        mid = msg.get("message_id")
        if not isinstance(mid, int) or mid <= 0:
            raise BotError("Recibo do Telegram incompleto")
        receipt = {"reservation": info["id"], "status": "sent", "message_id": mid}
    finally:
        # Até erro HTTP pode representar resultado incerto: jamais repetir POST aqui.
        result_file.write_text(json.dumps(receipt, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Telegram:", receipt["status"])
    if receipt["status"] != "sent":
        raise BotError("Não houve confirmação do envio; revisar canal e execução")


def finish(result_file: Path, prepared: Path) -> None:
    info = json.loads(prepared.read_text(encoding="utf-8"))
    if not info.get("ready"):
        return
    result = (json.loads(result_file.read_text(encoding="utf-8"))
              if result_file.exists() else {"reservation": info["id"], "status": "uncertain"})
    if result.get("reservation") != info["id"]:
        raise BotError("Recibo não corresponde à reserva")
    status = result.get("status")
    if status not in ("sent", "uncertain"):
        raise BotError("Status de envio desconhecido")
    state = read_state()
    matching = [e for e in state["events"] if e.get("reservation") == info["id"]]
    if len(matching) != 1:
        raise BotError("Reserva ausente ou duplicada")
    matching[0]["status"] = status
    if status == "sent":
        matching[0]["message_id"] = result["message_id"]
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Registro final:", status)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("preview", "check", "prepare", "send", "finish", "status"))
    parser.add_argument("--file", type=Path, help="JSON preparado")
    parser.add_argument("--receipt", type=Path, help="Recibo local")
    args = parser.parse_args()
    if args.action == "check":
        preflight()
        print("Telegram: bot administrador e canal confirmados")
    elif args.action == "status":
        state = read_state()
        print(json.dumps(state, ensure_ascii=False, indent=2))
    elif args.action == "preview":
        p = choose(now_utc())
        print(json.dumps(build_reservation(p, now_utc()) if p else {"ready": False},
                         ensure_ascii=False, indent=2))
    elif args.action == "prepare":
        if not args.file:
            parser.error("--file obrigatório")
        prepare(args.file)
    elif args.action in ("send", "finish"):
        if not args.file or not args.receipt:
            parser.error("--file e --receipt obrigatórios")
        if args.action == "send":
            send(args.file, args.receipt)
        else:
            finish(args.receipt, args.file)


if __name__ == "__main__":
    try:
        main()
    except (BotError, OSError, ValueError, subprocess.CalledProcessError) as exc:
        print("ERRO: " + str(exc), file=sys.stderr)
        raise SystemExit(1)
