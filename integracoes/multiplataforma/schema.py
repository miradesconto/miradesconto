"""Modelo universal independente dos IDs e APIs das lojas (sem rede)."""
from __future__ import annotations

import json
import math
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

PLATFORMS = {"mercadolivre", "shopee", "amazon"}
AFFILIATE_HOSTS = {
    "mercadolivre": {"meli.la", "mercadolivre.com.br", "www.mercadolivre.com.br"},
    "shopee": {"s.shopee.com.br", "shopee.com.br", "www.shopee.com.br", "shope.ee"},
    "amazon": {"amzn.to", "amazon.com.br", "www.amazon.com.br", "amazon.com", "www.amazon.com"},
}

class CatalogError(ValueError):
    pass


def secure_url(value, hosts=None, nullable=False):
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not value or re.search(r'[\s<>"\x00-\x1f]', value):
        raise CatalogError("URL ausente ou insegura")
    try:
        u = urlsplit(value)
        if u.scheme != "https" or not u.hostname or u.username or u.password or u.port not in (None, 443):
            raise CatalogError("URL deve usar HTTPS sem credenciais")
        if hosts and u.hostname.lower() not in hosts:
            raise CatalogError("Host de afiliado incompatível")
    except ValueError as exc:
        raise CatalogError("URL malformada") from exc
    return value


def valid_price(value):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise CatalogError("Preço inválido")
    return float(value)


def validate_offer(item):
    if not isinstance(item, dict) or item.get("platform") not in PLATFORMS:
        raise CatalogError("Plataforma inválida")
    platform = item["platform"]
    pid = str(item.get("platform_id", "")).strip()
    if not pid:
        raise CatalogError("platform_id obrigatório")
    secure_url(item.get("affiliate_url"), AFFILIATE_HOSTS[platform])
    if item.get("product_url") is not None:
        secure_url(item["product_url"])
    valid_price(item.get("price"))
    if item.get("currency", "BRL") != "BRL":
        raise CatalogError("Moeda não suportada")
    if item.get("in_stock") is not None and type(item["in_stock"]) is not bool:
        raise CatalogError("Estoque inválido")
    status = item.get("price_status", "unverified")
    if status not in ("unverified", "verified", "missing"):
        raise CatalogError("Status de preço inválido")
    checked = item.get("price_verified_at")
    if status == "verified":
        if not checked or item.get("price") is None:
            raise CatalogError("Preço verificado exige valor e data")
        try:
            stamp = datetime.fromisoformat(str(checked).replace("Z", "+00:00"))
        except ValueError as exc:
            raise CatalogError("Data de preço inválida") from exc
        if stamp.tzinfo is None:
            raise CatalogError("Data sem fuso não é evidência")
    return item


def validate_product(product):
    if not isinstance(product, dict):
        raise CatalogError("Produto inválido")
    if not re.fullmatch(r"prod_[a-z0-9_]+", str(product.get("id", ""))):
        raise CatalogError("ID interno inválido")
    for field in ("title", "description", "category"):
        if not isinstance(product.get(field), str) or (field != "description" and not product[field].strip()):
            raise CatalogError("Metadado inválido: " + field)
    if not isinstance(product.get("featured", False), bool):
        raise CatalogError("featured deve ser booleano")
    secure_url(product.get("image_url"), nullable=True)
    offers = product.get("offers")
    if not isinstance(offers, list) or not offers:
        raise CatalogError("Produto sem ofertas")
    seen = set()
    for offer in offers:
        validate_offer(offer)
        key = (offer["platform"], str(offer["platform_id"]))
        if key in seen:
            raise CatalogError("Oferta duplicada no produto")
        seen.add(key)
    return product


def build_catalog(products):
    seen_ids, seen_offers = set(), set()
    for product in products:
        validate_product(product)
        if product["id"] in seen_ids:
            raise CatalogError("ID interno duplicado")
        seen_ids.add(product["id"])
        for offer in product["offers"]:
            key = (offer["platform"], str(offer["platform_id"]))
            if key in seen_offers:
                raise CatalogError("Mesmo anúncio em dois produtos")
            seen_offers.add(key)
    return {"schema_version": 2, "products": products}


def read_catalog(path):
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    if obj.get("schema_version") != 2:
        raise CatalogError("Schema universal não suportado")
    return build_catalog(obj.get("products", []))


def write_preview(products, destination):
    destination = Path(destination)
    if destination.exists():
        raise CatalogError("Arquivo de saída já existe; nunca sobrescrever sem revisão")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(build_catalog(products), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destination


def from_legacy_ml(p, universal_id=None):
    """Lê um registro ML legado sem mudar ID nem URL do cadastro antigo."""
    original = str(p.get("id", ""))
    if not re.fullmatch(r"MLB\d{7,}", original):
        raise CatalogError("ID ML inválido")
    affiliate = p.get("affiliate_url") or p.get("affiliateUrl")
    image = p.get("custom_image") or p.get("image_url") or p.get("imageUrl")
    evidence = p.get("priceCheck") if isinstance(p.get("priceCheck"), dict) else {}
    price = p.get("price")
    verified = bool(evidence.get("status") == "verified" and evidence.get("checkedAt") and price is not None)
    offer = {
        "platform": "mercadolivre", "platform_id": original, "affiliate_url": affiliate,
        "product_url": p.get("productUrl"), "price": price, "currency": "BRL",
        "in_stock": None, "price_status": "verified" if verified else "unverified",
        "price_verified_at": evidence.get("checkedAt") if verified else None,
    }
    product = {
        "id": universal_id or "prod_ml_" + original[3:], "title": p.get("title") or p.get("name", ""),
        "description": p.get("description", ""), "category": p.get("category", "Outros"),
        "image_url": image, "featured": bool(p.get("featured", False)), "offers": [offer],
    }
    validate_product(product)
    return product
