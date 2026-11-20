#!/usr/bin/env python3
"""Validação de capa obrigatória para artigos novos ou alterados antes do deploy.

Artigos legados não tocados ficam fora da migração para evitar bloqueio massivo.
Sem rede: exige capa local original (custom_image/cover/image) válida para todo
artigo publicado criado ou alterado no commit em análise.
"""
import argparse
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
ARTICLES = ROOT / "_artigos"
SUPPORTED = {".png", ".jpg", ".jpeg", ".webp", ".svg"}
MIN_RASTER_BYTES = 10_000


def frontmatter(text):
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not match:
        raise ValueError("Front matter YAML ausente.")
    fields = {}
    for line in match.group(1).splitlines():
        found = re.match(r"^([\w-]+):\s*(.*?)\s*$", line)
        if not found:
            continue
        key, value = found.groups()
        if value.startswith('"') and value.endswith('"'):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                value = value[1:-1]
        elif value.startswith("'") and value.endswith("'"):
            value = value[1:-1]
        fields[key] = value
    return fields


def check_image(raw):
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("Capa ausente: informe custom_image, cover ou image.")
    parsed = urlsplit(raw)
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
        raise ValueError("Para artigos novos, use arquivo de capa local do repositório, não URL externa.")
    src = unquote(parsed.path)
    if not src.startswith("/assets/") or "\\" in src:
        raise ValueError("Capa precisa estar em /assets/ e sem atalhos externos.")
    target = (ROOT / src.lstrip("/")).resolve()
    assets = (ROOT / "assets").resolve()
    if not target.is_relative_to(assets) or target.suffix.lower() not in SUPPORTED:
        raise ValueError("Formato ou caminho da imagem inválido.")
    if not target.is_file():
        raise ValueError(f"Imagem de capa não encontrada no GitHub: {src}")
    data = target.read_bytes()
    if target.suffix.lower() == ".png":
        if len(data) < MIN_RASTER_BYTES or not data.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("PNG de capa muito pequeno ou inválido.")
    elif target.suffix.lower() in {".jpg", ".jpeg"}:
        if len(data) < MIN_RASTER_BYTES or not (data.startswith(b"\xff\xd8") and data.endswith(b"\xff\xd9")):
            raise ValueError("JPG de capa muito pequeno ou inválido.")
    elif target.suffix.lower() == ".webp":
        if len(data) < MIN_RASTER_BYTES or not (data[:4] == b"RIFF" and data[8:12] == b"WEBP"):
            raise ValueError("WebP de capa muito pequeno ou inválido.")
    else:
        if len(data) < 500 or b"<svg" not in data[:1500] or b"</svg>" not in data:
            raise ValueError("SVG de capa inválido ou vazio.")
    return src


def validate_one(file):
    fields = frontmatter(file.read_text(encoding="utf-8"))
    if str(fields.get("status", "")).strip() != "publicado" or str(fields.get("published", "")).lower() != "true":
        return "rascunho/arquivado — sem exigência de capa para publicar"
    # A capa editorial deve ser explicitamente atribuída ao artigo.
    raw = fields.get("custom_image") or fields.get("cover") or fields.get("image")
    return check_image(raw)


def changed_articles(base):
    cmd = ["git", "diff", "--name-only", "--diff-filter=ACMR", base, "HEAD", "--", "_artigos/"]
    output = subprocess.check_output(cmd, cwd=ROOT, text=True)
    return [ROOT / name for name in output.splitlines() if name.endswith(".md") and (ROOT / name).is_file()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", help="Commit base de comparação; verifica artigos criados/alterados.")
    parser.add_argument("--all", action="store_true", help="Audita todos os artigos, inclusive legados.")
    args = parser.parse_args()
    if not args.base and not args.all:
        parser.error("Informe --base ou --all.")
    files = sorted(ARTICLES.glob("*.md")) if args.all else changed_articles(args.base)
    errors = []
    tested = 0
    for path in files:
        try:
            result = validate_one(path)
            print(f"OK {path.name}: {result}")
            tested += 1
        except (ValueError, OSError) as exc:
            errors.append(f"{path.name}: {exc}")
    if errors:
        for err in errors:
            print("BLOQUEADO: " + err)
        raise SystemExit(f"{len(errors)} artigo(s) sem capa aprovada; corrija antes de publicar.")
    print(f"OK: {tested} arquivo(s) editorial(is) revisado(s); nenhum novo post publicado sem capa.")


if __name__ == "__main__":
    main()
