"""Shared rules for using a price observation; historical data is not verified."""
from datetime import datetime, timezone
import math
import re

MAX_PRICE_AGE_HOURS = 2


def price_review_reason(product):
    """Flag implausible offers, preserving historical observations and affiliate URLs.

    This narrow rule is not a substitute for merchant-side price validation.
    """
    price = product.get('price')
    name = str(product.get('name') or '')
    if (isinstance(price, (int, float)) and not isinstance(price, bool)
            and math.isfinite(price) and price >= 5000
            and re.search(r'\b(?:smart\s+)?tv\b|\btelevisor\b', name, re.I)
            and re.search(r'\b43\b', name)
            and re.search(r'\b(?:full\s*hd|fhd)\b', name, re.I)):
        return 'tv_43_fhd_above_review_limit'
    return None


def usable_price(product, now=None):
    evidence = product.get('priceCheck') or {}
    if not isinstance(evidence, dict): return False
    if evidence.get('status') != 'verified' or evidence.get('method') not in ('poly-card-v1', 'ml-sale-price-v1'): return False
    expected = product.get('itemId') if evidence.get('method') == 'ml-sale-price-v1' else product.get('id')
    if not expected or evidence.get('itemId') != expected or evidence.get('currency') != 'BRL': return False
    price = product.get('price')
    if isinstance(price, bool) or not isinstance(price, (int,float)) or not math.isfinite(price) or price <= 0: return False
    if evidence.get('price') != price or evidence.get('oldPrice') != product.get('oldPrice'): return False
    if product.get('available') is False: return False
    try:
        checked = datetime.fromisoformat(evidence['checkedAt'].replace('Z','+00:00'))
        if checked.tzinfo is None: return False
        age = ((now or datetime.now(timezone.utc)) - checked).total_seconds()
    except (KeyError, TypeError, ValueError, AttributeError): return False
    return 0 <= age <= MAX_PRICE_AGE_HOURS * 3600
