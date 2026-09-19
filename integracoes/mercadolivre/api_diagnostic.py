#!/usr/bin/env python3
"""Diagnostica o destino público embutido em um link afiliado existente."""
from __future__ import annotations

import html
import json
import re
from urllib.parse import urlparse, parse_qs
from urllib.request import Request, urlopen

KNOWN_AFFILIATE_URL = "https://meli.la/1TJh5DW"


def main() -> int:
    req = Request(
        KNOWN_AFFILIATE_URL,
        headers={
            "Accept": "text/html,application/xhtml+xml",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/153 Safari/537.36",
        },
        method="GET",
    )
    with urlopen(req, timeout=45) as response:
        final_url = response.geturl()
        status = response.status
        body = response.read(2_000_000).decode("utf-8", errors="replace")
    parsed = urlparse(final_url)
    params = parse_qs(parsed.query)
    decoded = html.unescape(body).replace("\\u002F", "/").replace("\\/", "/")
    ids = sorted(set(re.findall(r"MLB-?\d{7,}", decoded, flags=re.I)))[:20]
    urls = re.findall(r"https?://[^\"'<>\\\s]+", decoded)
    ml_urls = [u for u in urls if "mercadolivre.com.br" in u and "/social/" not in u][:10]
    print("AFFILIATE_REDIRECT_FORMAT=" + json.dumps({
        "http": status,
        "host": parsed.netloc,
        "path": parsed.path,
        "query_keys": sorted(params.keys()),
        "has_matt_word": bool(params.get("matt_word")),
        "has_matt_tool": bool(params.get("matt_tool") or params.get("matt_tool_id")),
        "body_bytes": len(body.encode("utf-8")),
        "mlb_ids": ids,
        "mercadolivre_target_urls": ml_urls,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
