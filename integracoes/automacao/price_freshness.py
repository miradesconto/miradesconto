#!/usr/bin/env python3
"""Detect insufficient fresh individual offers without changing price evidence."""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'integracoes'))
from qualidade import usable_price, price_review_reason


def assess(catalog, now=None, reserve_minutes=60):
    now = now or datetime.now(timezone.utc)
    published = set(catalog['publishedIds'])
    offers = [p for p in catalog['products'] if p['id'] in published
              and re.fullmatch(r'https://meli\.la/[A-Za-z0-9]+', p.get('affiliateUrl', ''))
              and p['affiliateUrl'] not in ('https://meli.la/1NguveN', 'https://meli.la/1pyBZm8')
              and p.get('affiliateLinkType') != 'list'
              and not price_review_reason(p)]
    fresh = sum(usable_price(p, now) for p in offers)
    lasting = sum(usable_price(p, now + timedelta(minutes=reserve_minutes)) for p in offers)
    return {'checkedAt': now.isoformat(), 'freshOffers': fresh,
            'offersWithReserve': lasting, 'minimumOffers': 10,
            'needsRefresh': lasting < 10}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-fresh', action='store_true')
    args = parser.parse_args()
    result = assess(json.loads((ROOT / 'dados/catalogo.json').read_text()))
    print(json.dumps(result, ensure_ascii=False))
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
            output.write('needed=' + str(result['needsRefresh']).lower() + '\n')
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as summary:
            summary.write(f"\nPreços recentes com link individual: **{result['freshOffers']}**. "
                          f"Ainda válidos daqui a 1 hora: **{result['offersWithReserve']}**.\n")
    if args.require_fresh and result['needsRefresh']:
        raise SystemExit('Cobertura insuficiente: menos de 10 ofertas válidas com reserva de 1 hora.')


if __name__ == '__main__':
    main()
