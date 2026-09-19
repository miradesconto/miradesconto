#!/usr/bin/env python3
"""Diagnostica preço atual embutido na página social pública de um link afiliado."""
from __future__ import annotations

import html
import json
import re
from urllib.request import Request, urlopen

KNOWN_AFFILIATE_URL = "https://meli.la/1TJh5DW"
TARGET_ITEM = "MLB4592320910"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/153 Safari/537.36"


def fetch_text(url: str):
    req = Request(url, headers={
        "Accept": "text/html,application/xhtml+xml",
        "User-Agent": UA,
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.7",
    }, method="GET")
    with urlopen(req, timeout=45) as response:
        return response.status, response.geturl(), response.read(3_000_000).decode("utf-8", errors="replace")


def main() -> int:
    status, final_url, body = fetch_text(KNOWN_AFFILIATE_URL)
    decoded = html.unescape(body).replace("\\u002F", "/").replace("\\/", "/")
    forms = [TARGET_ITEM, TARGET_ITEM.replace("MLB", "MLB-")]
    windows = []
    for form in forms:
        for match in list(re.finditer(re.escape(form), decoded, flags=re.I))[:5]:
            start = max(0, match.start() - 6000)
            end = min(len(decoded), match.end() + 6000)
            windows.append(decoded[start:end])
    combined = "\n".join(windows)
    price_pairs = []
    patterns = [
        ("json_price", r'"price"\s*:\s*([0-9]+(?:\.[0-9]+)?)'),
        ("json_original_price", r'"original_price"\s*:\s*([0-9]+(?:\.[0-9]+)?)'),
        ("json_originalPrice", r'"originalPrice"\s*:\s*([0-9]+(?:\.[0-9]+)?)'),
        ("money_fraction", r'andes-money-amount__fraction[^>]*>\s*([0-9\.]+)\s*<'),
    ]
    for label, pattern in patterns:
        vals = re.findall(pattern, combined, flags=re.I)
        if vals:
            price_pairs.append({"source": label, "values": vals[:12]})

    keys = sorted(set(re.findall(r'"([A-Za-z_][A-Za-z0-9_]{1,40})"\s*:', combined)))
    price_keys = [k for k in keys if any(w in k.lower() for w in ("price", "amount", "discount", "offer"))]
    result = {
        "http": status,
        "path": final_url.split("mercadolivre.com.br", 1)[-1].split("?", 1)[0],
        "target_occurrences": sum(len(re.findall(re.escape(f), decoded, flags=re.I)) for f in forms),
        "window_count": len(windows),
        "price_like_keys": price_keys[:50],
        "price_evidence": price_pairs,
    }
    print("SOCIAL_PRICE_DIAGNOSTIC=" + json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
