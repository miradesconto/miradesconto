#!/usr/bin/env python3
"""Descobre candidatos tech por vendedores relacionados, sem publicar ofertas.

Fonte: API oficial Mercado Livre. A busca pode ser negada a contas de afiliado.
Nenhum preço de busca ou desconto de referência vira promoção comprovada.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "integracoes"))
sys.path.insert(0, str(ROOT / "integracoes" / "mercadolivre"))
from tech_policy import category
from product_card import identity, Unconfirmed

API = "https://api.mercadolibre.com"
MLB_ID = re.compile(r"MLB\d{7,}$")
MAX_SEEDS = 16
MAX_SELLERS = 6
MAX_LISTINGS_PER_SELLER = 50
MAX_PRICE_CHECKS = 5


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward the bearer token, even to another official host.
        return None


class AccessError(RuntimeError):
    def __init__(self, status):
        self.status = status
        super().__init__(f"HTTP {status}")


class Client:
    def __init__(self, token: str):
        if not token or not token.strip():
            raise ValueError("ACCESS_TOKEN indisponível; não consultaremos dados oficiais sem autorização")
        self.token = token.strip()
        self.opener = build_opener(NoRedirect())

    def get(self, path: str):
        if not path.startswith("/") or "://" in path:
            raise ValueError("Caminho de API não permitido")
        request = Request(
            API + path,
            headers={"Authorization": "Bearer " + self.token,
                     "Accept": "application/json",
                     "User-Agent": "MiraDesconto-discovery-v1"},
            method="GET",
        )
        try:
            with self.opener.open(request, timeout=18) as response:
                # Never store or log authorization headers or returned opaque tokens.
                body = response.read(2_000_001)
        except HTTPError as exc:
            status = exc.code
            exc.close()
            raise AccessError(status) from None
        except (URLError, TimeoutError, OSError):
            raise RuntimeError("Falha de conexão na consulta oficial") from None
        if len(body) > 2_000_000:
            raise ValueError("Resposta da API excedeu limite seguro")
        return json.loads(body)


def _positive(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and value > 0)


def _seller_id(value):
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def seed_ids(catalog, limit=MAX_SEEDS):
    """Usa o acervo já curado, com no máximo 2 sementes por categoria primeiro."""
    by_id = {row.get("id"): row for row in catalog.get("products", [])
             if isinstance(row, dict)}
    seeded = []
    seen = set()
    by_category = {}
    for item_id in catalog.get("publishedIds", []):
        row = by_id.get(item_id)
        if not row or not MLB_ID.fullmatch(str(item_id)) or not row.get("affiliateUrl"):
            continue
        label = category(row)
        if not label or by_category.get(label, 0) >= 2 or item_id in seen:
            continue
        seeded.append(item_id)
        seen.add(item_id)
        by_category[label] = by_category.get(label, 0) + 1
        if len(seeded) >= limit:
            return seeded
    for item_id in catalog.get("publishedIds", []):
        if item_id not in seen and item_id in by_id and MLB_ID.fullmatch(str(item_id)):
            seeded.append(item_id)
            seen.add(item_id)
            if len(seeded) >= limit:
                break
    return seeded


def sellers_from_bulk(payload, seeds):
    """V2 usa status_code e body; 404/403 de um item não libera nenhum vendedor."""
    if not isinstance(payload, list):
        raise ValueError("API bulk sem lista de resultados")
    allowed = set(seeds)
    sellers = []
    for entry in payload:
        if not isinstance(entry, dict) or entry.get("status_code") != 200:
            continue
        body = entry.get("body")
        if not isinstance(body, dict) or entry.get("id") not in allowed:
            continue
        if body.get("id") != entry.get("id") or not _seller_id(body.get("seller_id")):
            continue
        seller = body["seller_id"]
        if seller not in sellers:
            sellers.append(seller)
    return sellers[:MAX_SELLERS]


def canonical_product_link(url, item_id):
    if not isinstance(url, str) or not MLB_ID.fullmatch(str(item_id)):
        return None
    try:
        parsed = urlsplit(url)
        if (parsed.scheme != "https" or parsed.username or parsed.password or
                parsed.port not in (None, 443) or not (
                    parsed.hostname == "mercadolivre.com.br"
                    or (parsed.hostname or "").endswith(".mercadolivre.com.br"))):
            return None
        actual, variation = identity(url)
        if actual != item_id or variation:
            return None
        # Drop tracking/opaque parameters after checking the original identity.
        if not re.match(r"^/MLB-\d{7,}(?:-|/|$)", parsed.path, re.I):
            return None
        return parsed._replace(query="", fragment="").geturl()
    except (ValueError, Unconfirmed):
        return None


def candidates_for_seller(response, seller_id, known_ids):
    if not isinstance(response, dict) or not isinstance(response.get("results"), list):
        raise ValueError("Resposta de busca não contém anúncios")
    result = []
    for product in response["results"][:MAX_LISTINGS_PER_SELLER]:
        if not isinstance(product, dict):
            continue
        item_id = product.get("id")
        actual_seller = (product.get("seller") or {}).get("id") if isinstance(product.get("seller"), dict) else None
        if (not isinstance(item_id, str) or not MLB_ID.fullmatch(item_id)
                or item_id in known_ids or actual_seller != seller_id
                or product.get("status", "active") != "active"):
            continue
        title = product.get("title")
        if not isinstance(title, str) or not 5 <= len(title.strip()) <= 180:
            continue
        label = category({"name": title})
        if not label:
            continue
        url = canonical_product_link(product.get("permalink"), item_id)
        if not url:
            continue
        result.append({
            "id": item_id,
            "title": title.strip(),
            "category": label,
            "sellerId": seller_id,
            "productUrl": url,
            "source": "mercadolivre-official-seller-search",
            "priceStatus": "unverified",
            "affiliateStatus": "not_registered",
            "identityStatus": "unverified",
            "variationStatus": "unverified",
            "historicalDiscountVerified": False,
            "eligibleForPublication": False,
        })
    return result


def attach_sale_price(candidate, response, checked_at):
    """Conferência independente do preço, NÃO certificação de boa promoção."""
    if not isinstance(response, dict) or response.get("currency_id") != "BRL":
        return candidate
    price = response.get("amount")
    old = response.get("regular_amount")
    if not _positive(price) or price > 2_000_000:
        return candidate
    if old is not None and (not _positive(old) or old > 2_000_000):
        return candidate
    result = dict(candidate)
    result["priceStatus"] = "confirmed_by_sale_price_api"
    result["currentPrice"] = round(price, 2)
    result["checkedAt"] = checked_at
    if old and old > price:
        result["storeReferencePrice"] = round(old, 2)
        result["storeAdvertisedDiscountPct"] = round((1 - price / old) * 100, 2)
    # Never call a store reference price "historical saving" or "real promotion".
    result["historicalDiscountVerified"] = False
    result["eligibleForPublication"] = False
    return result


def verify_item(candidate, payload):
    """Only a current, exact item without variations can receive an item price.

    Variant listings remain pending manual review; an item-level sale price
    cannot establish the price of a selected colour/size/configuration.
    """
    if not isinstance(payload, dict):
        return False
    if (payload.get("id") != candidate["id"]
            or payload.get("seller_id") != candidate["sellerId"]
            or payload.get("site_id") != "MLB"
            or payload.get("status") != "active"
            or payload.get("currency_id") != "BRL"
            or not canonical_product_link(payload.get("permalink"), candidate["id"])):
        return False
    candidate["identityStatus"] = "confirmed_by_item_api"
    variations = payload.get("variations")
    if not isinstance(variations, list):
        return False
    if variations:
        candidate["variationStatus"] = "requires_manual_selection"
        return False
    candidate["variationStatus"] = "no_variations_in_item_api"
    candidate["visualReviewStatus"] = "pending"
    return True


def choose_sellers(client, catalog, explicit_sellers):
    if explicit_sellers:
        return list(dict.fromkeys(explicit_sellers))[:MAX_SELLERS]
    seeds = seed_ids(catalog)
    if not seeds:
        return []
    params = urlencode({"ids": ",".join(seeds),
                        "attributes": "body.id,body.seller_id"})
    payload = client.get("/items/bulk?" + params)
    sellers = sellers_from_bulk(payload, seeds)
    if not sellers:
        for entry in payload:
            if isinstance(entry, dict) and entry.get("status_code") in (401, 403):
                raise AccessError(entry["status_code"])
    return sellers


def discover(catalog, client, explicit_sellers=(), now=None):
    when = now or datetime.now(timezone.utc)
    checked_at = when.isoformat(timespec="seconds")
    known_ids = {p["id"] for p in catalog.get("products", [])
                 if isinstance(p, dict) and isinstance(p.get("id"), str)}
    report = {
        "generatedAt": checked_at,
        "source": "api.mercadolibre.com",
        "mode": "review_only",
        "published": False,
        "method": "items-bulk + seller-search + sale-price",
        "sellersExamined": 0,
        "newCandidates": 0,
        "pricesConfirmed": 0,
        "priceAccess": "not_tested",
        "itemAccess": "not_tested",
        "discoveryAccess": "not_tested",
        "notes": [],
        "candidates": [],
    }
    try:
        sellers = choose_sellers(client, catalog, explicit_sellers)
    except AccessError as err:
        report["discoveryAccess"] = "blocked_http_" + str(err.status)
        report["notes"].append("API negou a identificação de vendedores; nenhuma oferta foi inferida")
        return report
    except (ValueError, RuntimeError):
        report["discoveryAccess"] = "unverified_error"
        report["notes"].append("Não foi possível confirmar a resposta de vendedores")
        return report
    if not sellers:
        report["discoveryAccess"] = "no_sources"
        report["notes"].append("Nenhuma semente ou vendedor autorizado; não há candidatos")
        return report
    discovered = {}
    for seller_id in sellers:
        try:
            data = client.get("/sites/MLB/search?" + urlencode(
                {"seller_id": seller_id, "limit": MAX_LISTINGS_PER_SELLER}))
            candidates = candidates_for_seller(data, seller_id, known_ids)
            report["sellersExamined"] += 1
            report["discoveryAccess"] = "available"
            for row in candidates:
                discovered.setdefault(row["id"], row)
        except AccessError as err:
            report["discoveryAccess"] = "blocked_http_" + str(err.status)
            report["notes"].append("Busca por vendedor indisponível: HTTP " + str(err.status))
            if err.status in (401, 403):
                report["discoveryAccess"] = "blocked_http_" + str(err.status)
                break
        except (ValueError, RuntimeError):
            report["discoveryAccess"] = "unverified_error"
            report["notes"].append("Resposta ou conexão do vendedor não pôde ser verificada")
    rows = list(discovered.values())[:MAX_PRICE_CHECKS]
    denied_price = False
    for index, row in enumerate(rows):
        if denied_price:
            break
        try:
            item = client.get("/items/" + quote(row["id"]))
            if not verify_item(row, item):
                report["itemAccess"] = "unverified_item_or_variation"
                continue
            report["itemAccess"] = "available"
        except AccessError as err:
            report["itemAccess"] = "blocked_http_" + str(err.status)
            if err.status in (401, 403):
                break
            continue
        except (ValueError, RuntimeError):
            report["itemAccess"] = "unverified_error"
            continue
        try:
            price = client.get("/items/" + quote(row["id"]) +
                               "/sale_price?context=channel_marketplace")
            rows[index] = attach_sale_price(row, price, checked_at)
            if rows[index]["priceStatus"] == "confirmed_by_sale_price_api":
                report["pricesConfirmed"] += 1
                report["priceAccess"] = "available"
        except AccessError as err:
            report["notes"].append("Preço do anúncio indisponível: HTTP " + str(err.status))
            if err.status in (401, 403):
                report["priceAccess"] = "blocked_http_" + str(err.status)
                denied_price = True
        except (ValueError, RuntimeError):
            report["notes"].append("Preço de anúncio sem confirmação confiável")
    if not rows:
        report["notes"].append("Nenhum anúncio tech novo com ID e URL inequívocos encontrado")
    report["candidates"] = rows
    report["newCandidates"] = len(rows)
    return report


def parse_seller_ids(raw):
    if not raw.strip():
        return []
    if len(raw) > 120:
        raise ValueError("Lista de vendedores excessiva")
    entries = re.split(r"[,\s]+", raw.strip())
    if len(entries) > MAX_SELLERS or any(not re.fullmatch(r"[1-9]\d{0,13}", x) for x in entries):
        raise ValueError("Forneça até 6 IDs numéricos de vendedores, separados por vírgula")
    return [int(x) for x in entries]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seller-ids", default="")
    args = parser.parse_args(argv)
    # Reject destination escaping the action's isolated review directory.
    destination = args.output.resolve()
    if (destination.suffix != ".json"
            or not destination.is_relative_to((ROOT / "preview").resolve())):
        raise ValueError("Arquivo de resultado deve ser JSON dentro de preview/")
    catalog = json.loads((ROOT / "dados/catalogo.json").read_text(encoding="utf-8"))
    client = Client(os.getenv("ACCESS_TOKEN", ""))
    result = discover(catalog, client, parse_seller_ids(args.seller_ids))
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    # API-controlled text must never echo the credential into an artifact.
    if client.token in serialized:
        raise ValueError("Resposta recusada por conter credencial")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(serialized,
                           encoding="utf-8")
    print("Descoberta: " + json.dumps({k: v for k, v in result.items()
             if k not in ("candidates", "notes")}, ensure_ascii=False))
    print("Aviso: 0 produtos publicados e nenhum link de afiliado criado.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, RuntimeError):
        print("Descoberta não concluída; entrada, credencial, resposta ou conexão inválida. Nenhum dado bruto registrado.", file=sys.stderr)
        raise SystemExit(1)
