"""Publica os três Pins aprovados após envio das artes originais ao repositório."""
import base64
import json
import os
from pathlib import Path
from urllib.parse import urlencode

from api import pinterest_request, find_existing_pin
from link_rules import affiliate_description, validate_ml_link

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "integracoes/pinterest/config.json"
IMAGES = {
    "aspire-go-i7": "acer-aspire-go-i7.png",
    "smart-tag-android": "smart-tag-android.png",
    "camera-a28b": "camera-wifi-a28b.png",
}

def find_board(token, name):
    bookmark = None
    seen = set()
    matches = []
    while True:
        params = {"page_size": 250}
        if bookmark:
            params["bookmark"] = bookmark
        page = pinterest_request(token, "/boards?" + urlencode(params))
        if not isinstance(page, dict) or not isinstance(page.get("items"), list):
            raise RuntimeError("Não foi possível consultar pastas da conta Pinterest.")
        for board in page["items"]:
            if isinstance(board, dict) and board.get("name", "").strip().casefold() == name.strip().casefold():
                matches.append(board)
        bookmark = page.get("bookmark")
        if not bookmark:
            break
        if bookmark in seen:
            raise RuntimeError("Paginação de pastas repetida.")
        seen.add(bookmark)
    if len(matches) != 1 or not str(matches[0].get("id", "")).isdigit():
        raise RuntimeError(f"Esperada uma pasta com nome exato; encontradas {len(matches)}. Verifique o Pinterest.")
    return str(matches[0]["id"])

def main():
    token = os.getenv("PINTEREST_ACCESS_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Falta PINTEREST_ACCESS_TOKEN nos GitHub Secrets.")
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    if cfg.get("board", {}).get("name") != "Ofertas de Tecnologia e Achadinhos | MiraDesconto":
        raise RuntimeError("Nome da pasta não corresponde ao aprovado.")
    offers = cfg.get("affiliateOffers", [])
    if len(offers) != 3 or {o["id"] for o in offers} != set(IMAGES):
        raise RuntimeError("Ofertas inesperadas; publicação bloqueada.")
    # Falha antes de publicar qualquer item se faltar uma arte.
    for name in IMAGES.values():
        path = ROOT / "assets/pinterest" / name
        if not path.is_file() or path.stat().st_size < 20000:
            raise RuntimeError("Arte original ausente ou pequena: " + name)
    board_id = find_board(token, cfg["board"]["name"])
    print("Pasta Pinterest encontrada: " + cfg["board"]["name"] + " (ID " + board_id + ")")
    for offer in offers:
        link = validate_ml_link(offer["affiliateUrl"])
        existing = find_existing_pin(token, link)
        if existing:
            print("Já existe Pin para " + offer["id"] + "; ignorado.")
            continue
        path = ROOT / "assets/pinterest" / IMAGES[offer["id"]]
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        payload = {
            "board_id": board_id,
            "title": offer["title"],
            "description": affiliate_description(offer["caption"]),
            "link": link,
            "media_source": {
                "source_type": "image_base64",
                "content_type": "image/png",
                "data": data,
                "is_standard": True
            }
        }
        result = pinterest_request(token, "/pins", payload)
        if not isinstance(result, dict) or not result.get("id"):
            raise RuntimeError("Resposta de publicação incerta; verifique Pinterest antes de tentar novamente.")
        print("Pin publicado: " + offer["id"] + " — ID " + str(result["id"]))

if __name__ == "__main__":
    main()
