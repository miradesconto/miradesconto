"""Shared rules for using a price observation; historical data is not verified."""
from datetime import datetime, timezone
import math

MAX_PRICE_AGE_HOURS = 24


def usable_price(product, now=None):
    evidence = product.get('priceCheck') or {}
    if not isinstance(evidence, dict): return False
    if evidence.get('status') != 'verified' or evidence.get('method') != 'poly-card-v1': return False
    if evidence.get('itemId') != product.get('id') or evidence.get('currency') != 'BRL': return False
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
