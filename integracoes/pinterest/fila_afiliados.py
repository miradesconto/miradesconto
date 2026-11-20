"""Fila Pinterest somente para links diretos de afiliados aprovados."""
import argparse
import base64
import hashlib
import json
import os
import re
from pathlib import Path
from urllib.parse import urlsplit

from api import pinterest_request
from fila_automatica import checkpoint, existing_pins, normalize
from publicar_lote import find_board
from link_rules import affiliate_description, validate_ml_link

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "integracoes/pinterest/fila_afiliados.json"
STATE = ROOT / "integracoes/pinterest/estado_afiliados.json"
SHOPEE_HOSTS = {"s.shopee.com.br", "shopee.com.br", "www.shopee.com.br"}


def validate_affiliate(url, merchant):
    if merchant == "mercado_livre":
        return validate_ml_link(url)
    if merchant != "shopee" or not isinstance(url, str) or url != url.strip():
        raise ValueError("Marketplace ou link não aprovado.")
    if re.search(r"[\\x00-\\x20\\x7f]", url):
        raise ValueError("Link com caracteres inválidos.")
    try:
        parsed = urlsplit(url)
        valid = (parsed.scheme == "https" and parsed.hostname in SHOPEE_HOSTS
                 and parsed.port is None and not parsed.username and not parsed.password
                 and not parsed.fragment and parsed.path not in ("", "/"))
    except ValueError:
        valid = False
    if not valid:
        raise ValueError("Use apenas URL HTTPS oficial da Shopee para um produto.")
    return url


def validate(post, root=ROOT):
    if post.get("approved") is not True:
        raise ValueError("Pin não aprovado.")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", post.get("key", "")):
        raise ValueError("Identificador inválido.")
    link = validate_affiliate(post.get("affiliate"), post.get("merchant"))
    if post.get("link") != link:
        raise ValueError("O destino do Pin deve ser exatamente o link de afiliado.")
    if not isinstance(post.get("title"), str) or not 1 <= len(post["title"]) <= 100:
        raise ValueError("Título inválido.")
    description = affiliate_description(post.get("description"))
    if not isinstance(post.get("confirmed_channel"), bool) or not post["confirmed_channel"]:
        raise ValueError("Confirme que Pinterest está autorizado no programa de afiliados.")
    image = (root / post.get("image", "")).resolve()
    if not image.is_relative_to((root / "assets/pinterest").resolve()) or image.suffix.lower() != ".png":
        raise ValueError("Arte precisa ser PNG em assets/pinterest.")
    if not re.fullmatch(r"[a-f0-9]{64}", post.get("sha256", "")):
        raise ValueError("Hash da arte inválido.")
    if hashlib.sha256(image.read_bytes()).hexdigest() != post["sha256"]:
        raise ValueError("Arte mudou após aprovação.")
    return image, description


def run(queue, state, token, publish=False, save=None, root=ROOT, limit=1):
    if queue.get("schemaVersion") != 1 or not isinstance(queue.get("posts"), list):
        raise ValueError("Fila inválida.")
    if queue.get("boardName") != "Ofertas de Tecnologia e Achadinhos | MiraDesconto":
        raise ValueError("Pasta não aprovada.")
    if state.get("schemaVersion") != 1 or not isinstance(state.get("posts"), dict):
        raise ValueError("Histórico inválido.")
    approved = [post for post in queue["posts"] if post.get("approved") is True]
    if len({post.get("key") for post in approved}) != len(approved):
        raise ValueError("Identificadores repetidos.")
    validated = [(post, *validate(post, root)) for post in approved]
    if not publish:
        print(f"PRÉVIA: {len(validated)} Pins de afiliados aprovados.")
        return
    if not token:
        raise RuntimeError("PINTEREST_ACCESS_TOKEN ausente.")
    if any(item.get("status") == "uncertain" for item in state["posts"].values()):
        raise RuntimeError("Envio incerto: revisão manual necessária.")
    save = save or (lambda s: checkpoint(s, path=STATE, persist_git=True))
    existing = existing_pins(token)
    board = find_board(token, queue["boardName"])
    count = 0
    for post, image, description in validated:
        key, link = post["key"], post["affiliate"]
        found = existing.get(normalize(link))
        if found:
            if state["posts"].get(key, {}).get("pinId") != found:
                state["posts"][key] = {"status": "existing", "pinId": found, "link": link}
                save(state)
            continue
        if key in state["posts"] or count >= limit:
            continue
        state["posts"][key] = {"status": "uncertain", "link": link}
        save(state)  # Persistir antes do POST; jamais reenvio cego.
        result = pinterest_request(token, "/pins", {
            "board_id": board,
            "title": post["title"],
            "description": description,
            "link": link,
            "alt_text": post["title"] + " — divulgação de afiliado MiraDesconto",
            "media_source": {"source_type": "image_base64", "content_type": "image/png",
                             "is_standard": True,
                             "data": base64.b64encode(image.read_bytes()).decode("ascii")}
        })
        pin_id = str(result.get("id", "")) if isinstance(result, dict) else ""
        if not pin_id.isdigit():
            raise RuntimeError("Resposta incerta: verificar Pinterest antes de repetir.")
        verified = pinterest_request(token, "/pins/" + pin_id)
        if normalize(verified.get("link", "")) != normalize(link) or str(verified.get("board_id")) != board:
            raise RuntimeError("Pin criado, mas destino não confirmado; fila pausada.")
        state["posts"][key] = {"status": "published", "pinId": pin_id, "link": link}
        save(state)
        existing[normalize(link)] = pin_id
        count += 1
        print(f"PUBLICADO {key}: https://www.pinterest.com/pin/{pin_id}/")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    if args.publish and (os.getenv("GITHUB_ACTIONS") != "true"
                         or os.getenv("GITHUB_REF") != "refs/heads/main"):
        raise RuntimeError("Publicação restrita ao workflow na main.")
    run(json.loads(QUEUE.read_text(encoding="utf-8")),
        json.loads(STATE.read_text(encoding="utf-8")),
        os.getenv("PINTEREST_ACCESS_TOKEN", "").strip(), publish=args.publish)


if __name__ == "__main__":
    main()
