#!/usr/bin/env python3
"""MiraBot: safe, manual affiliate-link intake, separate from site publication.

This tool never manufactures referral parameters, never stores browser sessions
and never asserts that a URL earns commission. Registration is delegated to the
existing exact-item, price-verified import_links.py.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from import_links import affiliate
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'integracoes'))
import catalogo

MAX_LINKS = 20
MAX_INPUT_LENGTH = 4000


def parse_links(raw):
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError('Informe de 1 a 20 links de afiliado do Mercado Livre')
    if len(raw) > MAX_INPUT_LENGTH:
        raise ValueError('Entrada muito longa; limite de 4000 caracteres')
    links = list(dict.fromkeys(p for p in re.split(r'[\s,;]+', raw.strip()) if p))
    if not 1 <= len(links) <= MAX_LINKS:
        raise ValueError('Envie entre 1 e 20 links por execução')
    if any(not affiliate(link) for link in links):
        raise ValueError('Aceitos apenas links oficiais HTTPS meli.la ou Mercado Livre /sec/')
    return links


def build_preview(links, catalog, registered):
    products = {p.get('id'): p for p in catalog.get('products', [])}
    by_link = {}
    for row in registered:
        if isinstance(row, dict) and isinstance(row.get('affiliateUrl'), str):
            by_link.setdefault(row['affiliateUrl'], []).append(row['id'])
    rows = []
    for link in links:
        known_ids = list(dict.fromkeys(by_link.get(link, [])))
        product = products.get(known_ids[0]) if len(known_ids) == 1 else None
        rows.append({
            'link': link,
            'status': 'cadastrado' if product else ('revisar_vinculo' if known_ids else 'aguardando_validacao'),
            'productId': product.get('id') if product else None,
            'title': product.get('name') if product else None,
            'commissionVerified': False,
            'readyToPublish': False if not product else product['id'] in catalog.get('publishedIds', []),
        })
    return {'generatedAt': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'mode': 'review_only', 'source': 'owner_supplied_affiliate_links',
            'linksReceived': len(links), 'links': rows,
            'note': 'A previa valida o formato e cadastros existentes. Links novos so serao verificados ao aplicar; comissao nao comprovada.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, help='Caminho de saida para relatorio JSON')
    args = parser.parse_args()
    links = parse_links(os.getenv('AFFILIATE_LINKS', ''))
    current = catalogo.load(ROOT)
    registry = catalogo.read_json(ROOT / 'links-afiliados.json')
    report = build_preview(links, current, registry)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text + '\n', encoding='utf-8')
    print('MiraBot: ' + str(report['linksReceived']) + ' links recebidos')
    for row in report['links']:
        print(row['status'] + ': ' + (row['productId'] or 'link novo'))
    if os.getenv('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as f:
            f.write('## MiraBot — conferência de links\n\n')
            f.write('| Situação | Quantidade |\n|---|---:|\n')
            for status in ('cadastrado', 'aguardando_validacao', 'revisar_vinculo'):
                f.write('| ' + status + ' | ' + str(sum(row['status'] == status for row in report['links'])) + ' |\n')
            f.write('\nNovos links exigem validação do produto e do preço. Nenhum link de afiliado é fabricado.\n')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print('MiraBot: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
