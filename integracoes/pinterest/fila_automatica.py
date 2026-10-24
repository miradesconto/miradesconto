"""Fila diária de artes aprovadas, com diário persistido ANTES de cada POST."""
import argparse
import base64
import hashlib
import html
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from api import pinterest_request
from link_rules import validate_ml_link
from publicar_lote import find_board

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "integracoes/pinterest/fila_aprovada.json"
STATE = ROOT / "integracoes/pinterest/estado_fila.json"
DESCRIPTION = ("Confira os pontos de atenção no guia do MiraDesconto. "
               "Publicidade: conteúdo com links de afiliado; podemos receber "
               "comissão por compras elegíveis.")


def normalize(link):
    p = urlsplit(str(link))
    query = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
             if not k.lower().startswith("utm_")]
    return urlunsplit((p.scheme.lower(), p.netloc.lower(),
                      p.path.rstrip("/"), urlencode(query), ""))


def existing_pins(token):
    links = {}
    bookmark = None
    seen = set()
    while True:
        params = {"page_size": 250}
        if bookmark:
            params["bookmark"] = bookmark
        page = pinterest_request(token, "/pins?" + urlencode(params))
        if not isinstance(page, dict) or not isinstance(page.get("items"), list):
            raise RuntimeError("Não foi possível conferir Pins existentes.")
        for pin in page["items"]:
            if isinstance(pin, dict) and pin.get("link") and pin.get("id"):
                links[normalize(pin["link"])] = str(pin["id"])
        bookmark = page.get("bookmark")
        if not bookmark:
            return links
        if bookmark in seen:
            raise RuntimeError("Paginação repetida; fila pausada.")
        seen.add(bookmark)


def validate(post, root=ROOT):
    if post.get("approved") is not True:
        raise ValueError("Item sem aprovação.")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", post.get("key", "")):
        raise ValueError("Chave inválida.")
    slug = post.get("slug", "")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise ValueError("Slug inválido.")
    if post.get("link") != "https://miradesconto.com.br/blog/" + slug + "/":
        raise ValueError("Destino diferente do guia aprovado.")
    validate_ml_link(post.get("affiliate"))
    title = post.get("title", "")
    if not isinstance(title, str) or not 1 <= len(title) <= 100 or any(ord(c) < 32 for c in title):
        raise ValueError("Título inválido.")
    image = (root / post.get("image", "")).resolve()
    allowed = (root / "assets/pinterest").resolve()
    if not image.is_relative_to(allowed) or image.suffix.lower() != ".png":
        raise ValueError("Arte fora de assets/pinterest.")
    if not re.fullmatch(r"[a-f0-9]{64}", post.get("sha256", "")):
        raise ValueError("Assinatura da arte ausente.")
    if hashlib.sha256(image.read_bytes()).hexdigest() != post["sha256"]:
        raise ValueError("Arte diferente da versão aprovada.")
    article = (root / "_artigos" / (slug + ".md")).read_text(encoding="utf-8")
    front = article.split("---", 2)
    if len(front) < 3 or not re.search(r"(?m)^published:\s*true\s*$", front[1]):
        raise ValueError("Guia não publicado.")
    if post["affiliate"] not in article:
        raise ValueError("Guia sem o link de afiliado aprovado.")
    return image


def verify_live(post):
    request = Request(post["link"], headers={"User-Agent": "MiraDesconto-queue/1"})
    with urlopen(request, timeout=25) as response:
        if normalize(response.geturl()) != normalize(post["link"]):
            raise RuntimeError("Guia redirecionou para outro destino.")
        body = response.read(2_000_001)
    if len(body) > 2_000_000 or post["affiliate"] not in html.unescape(body.decode("utf-8")):
        raise RuntimeError("Guia no ar não confirmou o link de afiliado; publicação pausada.")


def checkpoint(state, path=STATE, persist_git=False):
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if persist_git:
        relative = path.relative_to(ROOT).as_posix()
        subprocess.run(["git", "add", "--", relative], cwd=ROOT, check=True)
        subprocess.run(["git", "commit", "-m", "Registra estado da fila Pinterest", "--", relative],
                       cwd=ROOT, check=True)
        # Sem force ou rebase: conflito impede o POST e exige nova revisão.
        subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=ROOT, check=True)


def run(queue, state, token, publish=False, save=checkpoint, check_live=verify_live,
        root=ROOT, limit=2):
    posts = queue.get("posts")
    if queue.get("schemaVersion") != 1 or not isinstance(posts, list):
        raise ValueError("Fila inválida.")
    if queue.get("boardName") != "Ofertas de Tecnologia e Achadinhos | MiraDesconto":
        raise ValueError("Pasta diferente da aprovada.")
    if state.get("schemaVersion") != 1 or not isinstance(state.get("posts"), dict):
        raise ValueError("Histórico inválido.")
    approved = [p for p in posts if p.get("approved") is True]
    keys = [p.get("key") for p in approved]
    if len(set(keys)) != len(keys):
        raise ValueError("Chaves repetidas.")
    # Valida o lote inteiro antes de qualquer chamada de escrita.
    for post in approved:
        validate(post, root)
    if not publish:
        print(f"PRÉVIA: {len(approved)} itens aprovados; nenhum Pin enviado.")
        return
    if any(v.get("status") == "uncertain" for v in state["posts"].values()):
        raise RuntimeError("Há envio incerto. Reconciliar manualmente antes de retomar.")
    if not token:
        raise RuntimeError("PINTEREST_ACCESS_TOKEN ausente.")
    existing = existing_pins(token)
    board = find_board(token, queue["boardName"])
    count = 0
    for post in approved:
        key = post["key"]
        duplicate = existing.get(normalize(post["link"])) or existing.get(normalize(post["affiliate"]))
        if duplicate:
            if state["posts"].get(key, {}).get("pinId") != duplicate:
                state["posts"][key] = {"status": "existing", "pinId": duplicate}
                save(state)
            print(f"JÁ EXISTE {key}: https://www.pinterest.com/pin/{duplicate}/")
            continue
        if key in state["posts"] or count >= limit:
            continue
        check_live(post)
        image = validate(post, root)
        # Persistência remota precisa concluir ANTES do POST: em caso de queda,
        # a próxima execução pausa em vez de repetir um envio de resultado incerto.
        state["posts"][key] = {"status": "uncertain",
                              "startedAt": datetime.now(timezone.utc).isoformat(),
                              "link": post["link"]}
        save(state)
        result = pinterest_request(token, "/pins", {
            "board_id": board, "title": post["title"], "link": post["link"],
            "description": DESCRIPTION, "alt_text": post["title"],
            "media_source": {"source_type": "image_base64", "content_type": "image/png",
                             "is_standard": True,
                             "data": base64.b64encode(image.read_bytes()).decode("ascii")}
        })
        pin_id = str(result.get("id", "")) if isinstance(result, dict) else ""
        if not pin_id.isdigit():
            raise RuntimeError("Envio incerto. Conferir Pinterest antes de retomar.")
        verified = pinterest_request(token, "/pins/" + pin_id)
        if (normalize(verified.get("link", "")) != normalize(post["link"])
                or str(verified.get("board_id")) != board):
            raise RuntimeError("Pin criado; destino não confirmado. Fila pausada.")
        state["posts"][key] = {"status": "published", "pinId": pin_id,
                              "link": post["link"]}
        save(state)
        existing[normalize(post["link"])] = pin_id
        count += 1
        print(f"PUBLICADO {key}: https://www.pinterest.com/pin/{pin_id}/")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    if args.publish and (os.getenv("GITHUB_ACTIONS") != "true"
                         or os.getenv("GITHUB_REF") != "refs/heads/main"):
        raise RuntimeError("Publicação permitida somente no workflow da main.")
    run(json.loads(QUEUE.read_text(encoding="utf-8")),
        json.loads(STATE.read_text(encoding="utf-8")),
        os.getenv("PINTEREST_ACCESS_TOKEN", "").strip(), publish=args.publish,
        save=lambda state: checkpoint(state, persist_git=args.publish))


if __name__ == "__main__":
    main()
