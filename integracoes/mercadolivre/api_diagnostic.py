#!/usr/bin/env python3
"""Diagnostica preço atual em página pública do Mercado Livre a partir de link afiliado existente."""
from __future__ import annotations

import html
import json
import re
from urllib.request import Request, urlopen

KNOWN_AFFILIATE_URL = "https://meli.la/1TJh5DW"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/153 Safari/537.36"


def fetch_text(url: str):
    req = Request(url, headers={
        "Accept": "text/html,application/xhtml+xml",
        "User-Agent": UA,
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.7",
    }, method="GET")
    with urlopen(req, timeout=45) as response:
        return response.status, response.geturl(), response.read(3_000_000).decode("utf-8", errors="replace")


def extract_product_url(body: str):
    decoded = html.unescape(body).replace("\\u002F", "/").replace("\\/", "/")
    candidates = re.findall(r"https?://[^\"'<>\\\s]+", decoded)
    for url in candidates:
        if "mercadolivre.com.br" not in url:
            continue
        if "produto.mercadolivre.com.br/MLB-" in url or re.search(r"mercadolivre\.com\.br/.+/p/MLB\d+", url, re.I):
            return url
    return None


def walk_json(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_json(child)


def parse_price(body: str):
    evidence = []
    for match in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', body, flags=re.I | re.S):
        raw = html.unescape(match.group(1)).strip()
        try:
            data = json.loads(raw)
        except Exception:
            continue
        for obj in walk_json(data):
            offers = obj.get("offers") if isinstance(obj, dict) else None
            if isinstance(offers, dict):
                for key in ("price", "lowPrice"):
                    val = offers.get(key)
                    if val not in (None, ""):
                        evidence.append(("jsonld.offers." + key, val))
            if isinstance(obj, dict) and obj.get("@type") == "Offer" and obj.get("price") not in (None, ""):
                evidence.append(("jsonld.offer.price", obj.get("price")))
    patterns = [
        ("meta.product.price", r'<meta[^>]+(?:property|itemprop)=["\'](?:product:price:amount|price)["\'][^>]+content=["\']([^"\']+)["\']'),
        ("meta.price.reverse", r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|itemprop)=["\'](?:product:price:amount|price)["\']'),
    ]
    for label, pattern in patterns:
        m = re.search(pattern, body, flags=re.I)
        if m:
            evidence.append((label, m.group(1)))
    for label, value in evidence:
        try:
            price = float(str(value).replace("R$", "").replace(" ", "").replace(",", "."))
            if 0 < price < 10_000_000:
                return round(price, 2), label
        except Exception:
            continue
    return None, None


def main() -> int:
    s1, social_url, social_body = fetch_text(KNOWN_AFFILIATE_URL)
    product_url = extract_product_url(social_body)
    result = {
        "affiliate_http": s1,
        "social_path": social_url.split("mercadolivre.com.br", 1)[-1].split("?", 1)[0],
        "product_url_found": bool(product_url),
    }
    if not product_url:
        print("PUBLIC_PRICE_DIAGNOSTIC=" + json.dumps(result, ensure_ascii=False))
        return 0
    s2, final_product_url, product_body = fetch_text(product_url)
    price, source = parse_price(product_body)
    item_match = re.search(r"MLB-?(\d{7,})", final_product_url, re.I)
    result.update({
        "product_http": s2,
        "item_id": f"MLB{item_match.group(1)}" if item_match else None,
        "body_bytes": len(product_body.encode("utf-8")),
        "price_found": price is not None,
        "price": price,
        "price_source": source,
    })
    print("PUBLIC_PRICE_DIAGNOSTIC=" + json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
