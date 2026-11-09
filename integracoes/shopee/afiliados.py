"""Consulta a Open API da Shopee e separa a prévia editorial dos relatórios privados."""

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
ENDPOINT = "https://open-api.affiliate.shopee.com.br/graphql"
PRODUCT_FIELDS = (
    "shopId itemId productName shopName productLink imageUrl priceMin priceMax "
    "sales ratingStar productCatIds periodEndTime"
)
ERROR_LABELS = {
    10000: "erro de sistema",
    10010: "consulta inválida",
    10020: "falha de autenticação",
    10030: "limite de tráfego",
    11000: "erro de processamento",
}


class ApiError(Exception):
    def __init__(self, message, retryable=False):
        super().__init__(message)
        self.retryable = retryable


class Shopee:
    def __init__(self, app_id, secret):
        self.app_id = app_id.strip()
        self.secret = secret.strip()
        if not self.app_id or not self.secret:
            raise ApiError("Secrets da Shopee ausentes ou vazios.")

    def call(self, operation, fields, *, mutation=False, **arguments):
        args = ", ".join(f"{key}: {value}" for key, value in arguments.items())
        selection = f"{operation}({args})" if args else operation
        kind = "mutation" if mutation else "query"
        query = f"{kind} {{ {selection} {{ {fields} }} }}"
        payload = json.dumps({"query": query}, separators=(",", ":")).encode()
        attempts = 1 if mutation else 2
        for attempt in range(attempts):
            try:
                return self.request(operation, payload)
            except ApiError as error:
                if not error.retryable or attempt + 1 == attempts:
                    raise
                time.sleep(2)

    def request(self, operation, payload):
        timestamp = str(int(time.time()))
        signature = hashlib.sha256(
            (self.app_id + timestamp).encode() + payload + self.secret.encode()
        ).hexdigest()
        request = Request(ENDPOINT, data=payload, headers={
            "Content-Type": "application/json",
            "Authorization": f"SHA256 Credential={self.app_id}, Timestamp={timestamp}, Signature={signature}",
        })
        try:
            with urlopen(request, timeout=20) as response:
                result = json.load(response)
        except HTTPError as error:
            raise ApiError(f"HTTP {error.code}", error.code == 429 or error.code >= 500) from None
        except (URLError, TimeoutError, ValueError):
            raise ApiError("falha de conexão ou resposta inválida", True) from None
        if not isinstance(result, dict):
            raise ApiError("resposta inesperada")
        if result.get("errors"):
            codes = [
                int(code) for error in result["errors"]
                if str(code := (error.get("extensions") or {}).get("code")).isdigit()
            ]
            message = ", ".join(f"{code} ({ERROR_LABELS.get(code, 'erro da Shopee')})" for code in codes)
            raise ApiError(message or "erro GraphQL sem código", any(c in (10000, 10030) for c in codes))
        data = (result.get("data") or {}).get(operation)
        if not isinstance(data, dict):
            raise ApiError("resposta sem dados da operação")
        return data

    def products(self, **filters):
        return self.call("productOfferV2", f"nodes {{ {PRODUCT_FIELDS} }}", **filters).get("nodes") or []


def quoted(value):
    return json.dumps(value, ensure_ascii=True)


def brl(value):
    try:
        price = Decimal(str(value))
        if price.is_finite() and 0 < price < 1_000_000:
            return format(price, ".2f")
    except InvalidOperation:
        pass
    return None


def product_summary(node):
    low, high = brl(node.get("priceMin")), brl(node.get("priceMax"))
    if not low or not high or Decimal(low) > Decimal(high):
        low = high = None
    return {
        "item_id": str(node["itemId"]),
        "shop_id": str(node["shopId"]),
        "title": node.get("productName"),
        "product_url": f"https://shopee.com.br/product/{int(node['shopId'])}/{int(node['itemId'])}",
        "merchant": node.get("shopName"),
        "price_min_brl": low,
        "price_max_brl": high,
        "sales": node.get("sales"),
        "rating": node.get("ratingStar"),
        "category_ids": node.get("productCatIds") or [],
        "offer_ends_at": node.get("periodEndTime"),
    }


def tokens(text):
    ascii_text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    return set(re.findall(r"[a-z0-9]+", ascii_text.lower()))


def feed_product(row, wanted):
    columns = row.get("columns")
    if isinstance(columns, str):
        try:
            columns = json.loads(columns)
        except ValueError:
            return None
    if not isinstance(columns, dict):
        return None
    title = columns.get("title")
    if not wanted or not isinstance(title, str) or not wanted <= tokens(title):
        return None
    link = columns.get("product_link")
    if not isinstance(link, str):
        return None
    parts = urlsplit(link)
    if parts.scheme != "https" or parts.netloc not in {"shopee.com.br", "www.shopee.com.br"}:
        return None
    match = re.search(r"(?:/product/|-i\.)(\d+)[/.](\d+)/?$", parts.path)
    if not match or match[2] != str(columns.get("itemid")):
        return None
    return {
        "shop_id": match[1], "item_id": match[2], "title": title,
        "product_url": f"https://shopee.com.br/product/{match[1]}/{match[2]}",
        "source": "feed_shopee",
    }


def catalog_rows():
    with (ROOT / "_data/shopee_ofertas.csv").open(encoding="utf-8", newline="") as source:
        rows = []
        for row in csv.DictReader(source):
            parts = urlsplit(row["product_url"])
            match = re.fullmatch(r"/product/(\d+)/(\d+)", parts.path)
            if parts.scheme != "https" or parts.netloc != "shopee.com.br" or not match:
                raise ApiError("URL inválida no catálogo Shopee")
            shop_id, item_id = map(int, match.groups())
            if str(item_id) != row["item_id"]:
                raise ApiError("ID diverge da URL no catálogo Shopee")
            rows.append((shop_id, item_id, row["product_url"]))
        return rows


def verified_product(api, shop_id, item_id):
    for filters in ({"shopId": shop_id}, {}):
        for node in api.products(itemId=item_id, limit=1, **filters):
            if (str(node.get("shopId")), str(node.get("itemId"))) == (str(shop_id), str(item_id)):
                return product_summary(node)
    raise ApiError("oferta não retornada para a loja e o anúncio informados")


def short_link(result):
    parts = urlsplit(result.get("shortLink") or "")
    if parts.scheme == "https" and parts.netloc == "s.shopee.com.br" and parts.path.strip("/"):
        return result["shortLink"]
    raise ApiError("link curto inválido")


def report_page(api, operation, **filters):
    records = []
    cursor = None
    for _ in range(20):
        page = api.call(operation, "nodes { netCommission } pageInfo { hasNextPage scrollId }",
                        limit=50, **filters, **({"scrollId": quoted(cursor)} if cursor else {}))
        records.extend(page.get("nodes") or [])
        info = page.get("pageInfo") or {}
        if not info.get("hasNextPage"):
            return {"records": len(records), "complete": True, "net_commission_brl": net_commission(records)}
        next_cursor = info.get("scrollId")
        if not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor
    return {"records": len(records), "complete": False, "net_commission_brl": None}


def net_commission(records):
    total = Decimal(0)
    for row in records:
        try:
            value = Decimal(str(row.get("netCommission")))
        except InvalidOperation:
            return None
        if not value.is_finite():
            return None
        total += value
    return format(total, ".2f")


def price_snapshot(snapshot):
    return {
        item: {"min": offer["price_min_brl"], "max": offer["price_max_brl"],
               "checked_at": snapshot["checked_at"]}
        for item, offer in snapshot["catalog"].items()
        if offer["price_min_brl"] and offer["price_max_brl"]
    }


def write_private(path, data):
    # Never used by the workflow in this public repository.
    with os.fdopen(
        os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w", encoding="utf-8"
    ) as target:
        json.dump(data, target, ensure_ascii=False, indent=2)
        target.write("\n")


def collect(api, args):
    now = int(time.time())
    statuses, private = {}, {}
    snapshot = {"checked_at": datetime.fromtimestamp(now, timezone.utc).isoformat(),
                "catalog": {}, "discovery": {}, "checks": statuses}

    def check(name, action):
        try:
            result = action()
        except ApiError as error:
            statuses[name] = {"status": "falhou", "detail": str(error)}
            print(f"{name}: {error}", flush=True)
            return None
        statuses[name] = {"status": "ok"}
        print(f"{name}: ok", flush=True)
        return result

    rows = catalog_rows()
    for shop_id, item_id, _ in rows:
        offer = check(f"catalogo/{item_id}", lambda: verified_product(api, shop_id, item_id))
        if offer is not None:
            snapshot["catalog"][str(item_id)] = offer

    discovery = snapshot["discovery"]
    top = check("produtos_em_alta", lambda: api.products(listType=2, limit=10))
    if top is not None:
        discovery["top_products"] = [product_summary(node) for node in top]

    categories = list(dict.fromkeys(
        offer["category_ids"][-1] for offer in snapshot["catalog"].values()
        if offer["category_ids"] and type(offer["category_ids"][-1]) is int
        and offer["category_ids"][-1] > 0
    ))
    candidates = [product_summary(node) for node in top or []]
    discovery["category_products"] = {}
    for category in categories[:3]:
        category_rows = check(f"ofertas_por_categoria/{category}",
                              lambda: api.products(listType=4, matchId=category, limit=10))
        if category_rows is not None:
            group = [product_summary(node) for node in category_rows]
            discovery["category_products"][str(category)] = group
            candidates.extend(group)
    wanted = tokens(args.keyword)
    relevant_categories = [
        offer["category_ids"][-1] for offer in snapshot["catalog"].values()
        if offer["category_ids"] and offer["category_ids"][-1] in categories
        and wanted & tokens(offer["title"])
    ]
    keyword_matches = {}
    for category in list(dict.fromkeys(relevant_categories or categories))[:3] if wanted else []:
        direct = check(f"busca_por_categoria/{category}", lambda: api.products(
            keyword=quoted(args.keyword), productCatId=category, limit=20))
        for node in direct or []:
            if wanted <= tokens(node.get("productName")):
                offer = product_summary(node)
                keyword_matches[(offer["shop_id"], offer["item_id"])] = offer
    fallback = {(offer["shop_id"], offer["item_id"]): offer
                for offer in [*snapshot["catalog"].values(), *candidates]
                if wanted and wanted <= tokens(offer["title"])}
    discovery["keyword_source"] = "shopee_categoria" if keyword_matches else None

    for op, key, fields in (
        ("shopOfferV2", "shops", "shopId shopName commissionRate periodEndTime"),
        ("shopeeOfferV2", "campaigns", "offerName offerType commissionRate periodEndTime"),
    ):
        data = check(op, lambda: api.call(op, f"nodes {{ {fields} }}", limit=10))
        if data is not None:
            records = data.get("nodes") or []
            private[key] = records
            discovery[key] = [{k: v for k, v in row.items() if k != "commissionRate"}
                              for row in records]

    feeds = check("listItemFeeds", lambda: api.call("listItemFeeds", "feeds { datafeedId totalCount feedMode }"))
    feed_entries = (feeds or {}).get("feeds") or []
    full_feeds = [f for f in feed_entries if f.get("datafeedId") and f.get("feedMode") == "FULL"]
    feed_results = {}
    known_ids = {str(item_id) for _, item_id, _ in rows}
    has_new_native = any(item_id not in known_ids for _, item_id in keyword_matches)
    if full_feeds:
        total_rows = 0
        has_more = False
        for feed in full_feeds[:2]:
            limit = 10 if has_new_native or not wanted else 500
            offset = 0
            page_has_more = False
            for _ in range(1 if limit == 10 else 4):
                feed_page = check(f"getItemFeedData/{total_rows}", lambda: api.call(
                    "getItemFeedData", "rows { columns } pageInfo { hasMore totalCount }",
                    datafeedId=quoted(feed["datafeedId"]), offset=offset, limit=limit,
                ))
                if feed_page is None:
                    break
                feed_rows = feed_page.get("rows") or []
                total_rows += len(feed_rows)
                page_has_more = bool((feed_page.get("pageInfo") or {}).get("hasMore"))
                for row in feed_rows:
                    offer = feed_product(row, wanted)
                    if offer:
                        feed_results[(offer["shop_id"], offer["item_id"])] = offer
                if not page_has_more or not feed_rows:
                    break
                offset += len(feed_rows)
            has_more = has_more or bool(feed_page is None or page_has_more)
        discovery["feed_sample"] = {"rows_checked": total_rows, "has_more": has_more}
    else:
        statuses["getItemFeedData"] = {"status": "bloqueado", "detail": "sem feed completo disponível"}

    if not keyword_matches:
        discovery["keyword_source"] = "feed_shopee" if feed_results else "filtro_local" if fallback else None
    all_matches = {**fallback, **feed_results, **keyword_matches}
    results = sorted(all_matches.values(), key=lambda offer: offer["item_id"] in known_ids)
    discovery["keyword_results"] = results[:20]
    discovery["keyword_new_count"] = sum(offer["item_id"] not in known_ids for offer in results[:20])
    print(f"Busca: {len(results[:20])} resultados, {discovery['keyword_new_count']} novos para o catálogo.",
          flush=True)

    if args.generate_links and rows:
        urls = [url for _, _, url in rows]
        first = urls[0]
        single = check("generateShortLink", lambda: short_link(api.call(
            "generateShortLink", "shortLink", mutation=True,
            input=f"{{originUrl: {quoted(first)}}}",
        )))
        if single:
            private["single_link"] = single

        def batch_links():
            items = ", ".join(f"{{originUrl: {quoted(url)}}}" for url in urls[:50])
            result = api.call("generateBatchShortLink", "links { originUrl shortLink success }",
                              mutation=True, input=f"{{links: [{items}]}}")
            links = {entry["originUrl"]: short_link(entry) for entry in result.get("links") or []
                     if entry.get("success") and entry.get("originUrl") in urls}
            private["batch_links"] = links
            if set(links) != set(urls[:50]):
                raise ApiError(f"lote incompleto: {len(links)} de {len(urls[:50])} links retornados")
            return links

        check("generateBatchShortLink", batch_links)
    else:
        for name in ("generateShortLink", "generateBatchShortLink"):
            statuses[name] = {"status": "não executado", "detail": "geração sob demanda"}

    private["conversions"] = check("conversionReport", lambda: report_page(
        api, "conversionReport", purchaseTimeStart=now - 7 * 86400, purchaseTimeEnd=now))
    if args.validation_id:
        private["validated"] = check("validatedReport", lambda: report_page(
            api, "validatedReport", validationId=args.validation_id))
    else:
        statuses["validatedReport"] = {"status": "bloqueado", "detail": "validationId exigido pela Shopee"}

    for operation, key in (("conversionReport", "conversions"), ("validatedReport", "validated")):
        if (report := private.get(key)) and not report["complete"]:
            statuses[operation] = {"status": "atenção", "detail": "paginação incompleta"}
    return snapshot, private


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keyword", default="Attack Shark X11")
    parser.add_argument("--validation-id", type=int)
    parser.add_argument("--generate-links", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--private-report", type=Path)
    parser.add_argument("--public-prices", type=Path)
    args = parser.parse_args()
    if args.validation_id is not None and args.validation_id <= 0:
        parser.error("--validation-id deve ser positivo")
    try:
        api = Shopee(os.getenv("SHOPEE_APP_ID", ""), os.getenv("SHOPEE_APP_SECRET", ""))
        snapshot, private = collect(api, args)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if args.public_prices and snapshot["catalog"]:
            args.public_prices.parent.mkdir(parents=True, exist_ok=True)
            args.public_prices.write_text(
                json.dumps(price_snapshot(snapshot), indent=2) + "\n", encoding="utf-8"
            )
        if args.private_report:
            write_private(args.private_report, private)
    except ApiError as error:
        print(error, file=sys.stderr)
        return 1
    return 0 if snapshot["catalog"] else 1


if __name__ == "__main__":
    sys.exit(main())
