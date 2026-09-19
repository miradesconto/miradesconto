#!/usr/bin/env python3
"""Localiza o objeto de dados do item-alvo na página social afiliada pública."""
from __future__ import annotations

import html
import json
import re
from urllib.request import Request, urlopen

KNOWN_AFFILIATE_URL = "https://meli.la/1TJh5DW"
TARGET_FORMS = {"MLB4592320910", "MLB-4592320910"}
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/153 Safari/537.36"


def fetch_text(url: str):
    req = Request(url, headers={
        "Accept": "text/html,application/xhtml+xml",
        "User-Agent": UA,
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.7",
    }, method="GET")
    with urlopen(req, timeout=45) as response:
        return response.status, response.geturl(), response.read(3_000_000).decode("utf-8", errors="replace")


def contains_target(value) -> bool:
    if isinstance(value, str):
        upper = value.upper()
        return any(form in upper for form in TARGET_FORMS)
    if isinstance(value, (int, float, bool)) or value is None:
        return False
    if isinstance(value, list):
        return any(contains_target(v) for v in value)
    if isinstance(value, dict):
        return any(contains_target(v) for v in value.values())
    return False


def compact(obj: dict):
    wanted = {}
    for key, value in obj.items():
        low = key.lower()
        if (
            key in {"id", "title", "name", "permalink", "url", "item_id", "itemId"}
            or any(word in low for word in ("price", "discount", "amount", "currency"))
        ):
            if isinstance(value, (str, int, float, bool)) or value is None:
                wanted[key] = value
            elif isinstance(value, dict):
                wanted[key] = {k: v for k, v in value.items() if isinstance(v, (str, int, float, bool)) and any(w in k.lower() for w in ("price", "amount", "currency", "value"))}
    return wanted


def walk(value, out):
    if isinstance(value, dict):
        if contains_target(value):
            c = compact(value)
            if c and c not in out:
                out.append(c)
        for child in value.values():
            walk(child, out)
    elif isinstance(value, list):
        for child in value:
            walk(child, out)


def main() -> int:
    status, final_url, body = fetch_text(KNOWN_AFFILIATE_URL)
    decoded = html.unescape(body).replace("\\u002F", "/").replace("\\/", "/")
    matches = []
    scripts = re.findall(r"<script[^>]*>(.*?)</script>", body, flags=re.I | re.S)
    parsed_scripts = 0
    for raw in scripts:
        text = html.unescape(raw).strip()
        if not text or not any(form in text.upper() for form in TARGET_FORMS):
            continue
        try:
            data = json.loads(text)
        except Exception:
            continue
        parsed_scripts += 1
        walk(data, matches)

    # Fallback: objetos JSON pequenos encontrados diretamente no HTML decodificado.
    for form in TARGET_FORMS:
        for m in list(re.finditer(re.escape(form), decoded, flags=re.I))[:10]:
            chunk = decoded[max(0, m.start() - 2500): min(len(decoded), m.end() + 2500)]
            for key in ("current_price", "previous_price", "price", "discount_label"):
                km = re.search(rf'"{key}"\s*:\s*("[^"]*"|[0-9]+(?:\.[0-9]+)?|null)', chunk, flags=re.I)
                if km:
                    matches.append({"source": "regex_window", "target": form, key: km.group(1).strip('"')})

    result = {
        "http": status,
        "path": final_url.split("mercadolivre.com.br", 1)[-1].split("?", 1)[0],
        "script_count": len(scripts),
        "parsed_target_scripts": parsed_scripts,
        "matches": matches[:30],
    }
    print("TARGET_OBJECT_DIAGNOSTIC=" + json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
