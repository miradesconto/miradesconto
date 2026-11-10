#!/usr/bin/env python3
"""MiraDesconto: cache local das fotos oficiais das ofertas na publicação.

O site deixa de depender de hotlink dos CDNs no navegador. Só aceita resposta
HTTP 200 com bytes de imagem confirmados. Mantém link afiliado intocado.
O catálogo é publicado APENAS se houver fotos locais utilizáveis.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlsplit

import requests

ROOT = Path(__file__).resolve().parents[2]
FEED = ROOT / "api/produtos.json"
DEST = ROOT / "assets/ofertas"
MAX_BYTES = 3_000_000
ALLOWED = {
    "cf.shopee.com.br",
    "down-br.img.susercontent.com",
    "down-bs-br.img.susercontent.com",
    "http2.mlstatic.com",
    "http2.mlstatic.com.br",
}
LOG = logging.getLogger("fotos")


def alternatives(url: str) -> list[str]:
    """Mantém a URL oficial; tenta CDN alternativo só no formato Shopee conhecido."""
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED or not parsed.path.startswith("/"):
        return []
    options = [url]
    if parsed.hostname in ("cf.shopee.com.br", "down-br.img.susercontent.com", "down-bs-br.img.susercontent.com"):
        if parsed.path.startswith("/file/") and re.fullmatch(r"/file/[A-Za-z0-9_-]{20,120}", parsed.path):
            for host in ("down-br.img.susercontent.com", "down-bs-br.img.susercontent.com"):
                alternate = f"https://{host}{parsed.path}"
                if alternate not in options:
                    options.append(alternate)
    return options


def extension(blob: bytes, content_type: str) -> str | None:
    """Não confia apenas em Content-Type: valida assinatura binária."""
    if len(blob) < 500 or len(blob) > MAX_BYTES:
        return None
    if blob.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if blob.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if blob[:4] == b"RIFF" and blob[8:12] == b"WEBP":
        return ".webp"
    return None


def download(url: str, getter=requests.get) -> tuple[bytes, str] | None:
    for candidate in alternatives(url):
        try:
            with getter(candidate, timeout=(6, 12), stream=True, allow_redirects=True,
                        headers={"User-Agent": "Mozilla/5.0 (compatible; MiraDesconto/1.0)",
                                 "Accept": "image/avif,image/webp,image/png,image/jpeg,image/*;q=0.8"}) as response:
                response.raise_for_status()
                if urlsplit(response.url).hostname not in ALLOWED:
                    continue
                data = bytearray()
                for chunk in response.iter_content(chunk_size=65536):
                    data.extend(chunk)
                    if len(data) > MAX_BYTES:
                        break
                data = bytes(data)
                ext = extension(data, response.headers.get("Content-Type", ""))
                if ext:
                    return data, ext
        except requests.RequestException:
            continue
    return None


def cached_image(row: dict, root: Path, getter=requests.get) -> str | None:
    img = row.get("imagem")
    target_dir = root / "assets/ofertas"
    if not isinstance(img, str):
        return None
    if img.startswith("/assets/ofertas/"):
        file = root / img.lstrip("/")
        return img if file.is_file() and extension(file.read_bytes(), "") else None

    # Nome estável por link individual: preservar a foto se uma API/CDN cair.
    link = row.get("link_afiliado")
    if not isinstance(link, str) or not link.startswith("https://"):
        return None
    stem = hashlib.sha256(link.encode("utf-8")).hexdigest()[:24]
    previous = next((p for p in target_dir.glob(stem + ".*")
                     if p.suffix in (".jpg", ".png", ".webp") and
                     extension(p.read_bytes(), "") is not None), None)
    fetched = download(img, getter=getter)
    if fetched is None:
        if previous:
            return "/assets/ofertas/" + previous.name
        return None

    blob, ext = fetched
    image_file = target_dir / (stem + ext)
    target_dir.mkdir(parents=True, exist_ok=True)
    if not image_file.exists() or image_file.read_bytes() != blob:
        image_file.write_bytes(blob)
    return "/assets/ofertas/" + image_file.name


def mirror_curated_shopee(root: Path = ROOT, getter=requests.get, workers: int = 7) -> dict[str, str]:
    """Espelha fotos dos destaques oficiais sem alterar links nem preços.

    O cadastro da Shopee mantém a URL remota; Liquid consulta este mapa local
    pelo item_id. Em instabilidade do CDN preservamos os arquivos anteriores.
    """
    source = root / "_data/shopee_gamer_publicados.json"
    output = root / "_data/shopee_fotos_locais.json"
    if not source.exists():
        return {}
    offers = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(offers, list):
        raise ValueError("Lista Shopee inválida")
    try:
        older = json.loads(output.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        older = {}
    if not isinstance(older, dict):
        older = {}
    unique = {}
    for offer in offers:
        if not isinstance(offer, dict):
            continue
        item_id = str(offer.get("item_id", ""))
        if not re.fullmatch(r"[0-9]{5,24}", item_id):
            continue
        url = offer.get("affiliate_url")
        image = offer.get("image_url")
        if not isinstance(url, str) or not url.startswith("https://s.shopee.com.br/"):
            continue
        if not isinstance(image, str):
            continue
        unique[item_id] = {"imagem": image, "link_afiliado": url}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        fetched = list(pool.map(lambda row: cached_image(row, root, getter), unique.values()))
    photos = {}
    for item_id, img in zip(unique, fetched):
        if img:
            photos[item_id] = img
        else:
            previous = older.get(item_id)
            if isinstance(previous, str) and re.fullmatch(
                r"/assets/ofertas/[a-f0-9]{24}\.(jpg|png|webp)", previous
            ) and (root / previous.lstrip("/")).is_file():
                photos[item_id] = previous
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(photos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    LOG.info("CACHE_SHOPEE_DESTAQUES_OK fotos=%d itens=%d", len(photos), len(unique))
    return photos


def mirror(root: Path = ROOT, getter=requests.get, workers: int = 7) -> dict:
    path = root / "api/produtos.json"
    products = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(products, list):
        raise ValueError("Feed não é uma lista.")
    products = [p for p in products if isinstance(p, dict)]
    if not products:
        raise ValueError("Feed vazio; cache anterior preservado.")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        photos = list(pool.map(lambda product: cached_image(product, root, getter), products))

    valid = []
    broken = 0
    for product, image in zip(products, photos):
        if not image:
            broken += 1
            continue
        item = dict(product)
        item["imagem"] = image
        valid.append(item)

    shopee = sum(p.get("loja") == "Shopee" for p in valid)
    ml = sum(p.get("loja") == "Mercado Livre" for p in valid)
    # Não substituir um feed existente por zero resultados se provedores caírem.
    if len(valid) < 4:
        raise ValueError(f"Apenas {len(valid)} fotos válidas; preservar feed anterior")
    # Conservar todas as ofertas do parceiro: sem garantia artificial de estoque infinito.
    snapshot = root / "_data/ofertas_automaticas.json"
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    output = json.dumps(valid, ensure_ascii=False, indent=2) + "\n"
    path.write_text(output, encoding="utf-8")
    snapshot.write_text(output, encoding="utf-8")
    LOG.info("CACHE_FOTOS_OK total=%d shopee=%d mercado_livre=%d removidos=%d", len(valid), shopee, ml, broken)
    mirror_curated_shopee(root, getter=getter, workers=workers)
    return {"total": len(valid), "shopee": shopee, "mercado_livre": ml, "sem_foto": broken}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    mirror(root=args.root)
