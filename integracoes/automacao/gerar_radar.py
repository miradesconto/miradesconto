#!/usr/bin/env python3
"""Generate the public MiraDesconto price radar from verified observations.

The radar never treats the store reference price as historical evidence. It only
compares the current verified price with observations archived for the same
listing and variation.
"""
from __future__ import annotations

import json
import math
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mercadolivre'))
from price_history import history_base
import requests

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "dados" / "catalogo.json"
HISTORY = ROOT / "historico"
OUTPUT = ROOT / "_data" / "radar.json"

TECH_CATEGORIES = {
    "Celulares",
    "Smart Home",
    "Setup",
    "Gaming",
    "Eletrônicos",
    "PC e hardware",
    "Áudio",
    "Impressoras",
    "Informática",
    "TVs e projetores",
    "Notebooks",
}

MAX_PRICE_AGE_HOURS = 36
MIN_OBSERVATIONS = 6
MIN_SPAN_HOURS = 24
MIN_ACTIONABLE_SPAN_DAYS = 7
MAX_FEATURED = 12
MAX_PER_CATEGORY = 3


def parse_time(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def money(value: float) -> str:
    text = f"{value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"R$ {text}"


def finite_price(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        return None
    return value


def anchor_time(products: list[dict]) -> datetime:
    checks = [
        parse_time((product.get("priceCheck") or {}).get("checkedAt"))
        for product in products
    ]
    valid = [value for value in checks if value is not None]
    return max(valid) if valid else datetime.now(timezone.utc)


def matching_rows(product: dict, data: dict, anchor: datetime) -> list[dict]:
    evidence = product.get("priceCheck") or {}
    if evidence.get("status") != "verified":
        return []

    expected = (
        product.get("itemId")
        if evidence.get("method") == "ml-sale-price-v1"
        else product.get("id")
    )
    variation = str(evidence.get("variationId") or "")
    rows: list[dict] = []

    for row in data.get("observations", []):
        at = parse_time(row.get("at"))
        price = finite_price(row.get("price"))
        if (
            at is None
            or at > anchor
            or at < anchor - timedelta(days=180)
            or price is None
            or row.get("itemId") != expected
            or str(row.get("variationId") or "") != variation
        ):
            continue
        rows.append({"at": at, "price": price})

    return sorted(rows, key=lambda row: row["at"])


def stats(rows: list[dict], anchor: datetime, days: int) -> dict | None:
    selected = [row for row in rows if row["at"] >= anchor - timedelta(days=days)]
    if not selected:
        return None
    values = [row["price"] for row in selected]
    average = sum(values) / len(values)
    return {
        "observations": len(values),
        "min": round(min(values), 2),
        "avg": round(average, 2),
        "max": round(max(values), 2),
        "minText": money(min(values)),
        "avgText": money(average),
        "maxText": money(max(values)),
    }


def classify(current: float, rows: list[dict]) -> tuple[str, int, str, float, float]:
    values = [row["price"] for row in rows]
    minimum = min(values)
    maximum = max(values)
    average = sum(values) / len(values)
    delta = (current / average - 1) * 100
    range_pct = (maximum / minimum - 1) * 100 if minimum else 0

    tolerance = max(0.01, minimum * 0.0001)
    meaningful_range = range_pct >= 1

    if meaningful_range and current <= minimum + tolerance:
        label = "Menor observado"
        if delta <= -5:
            strength = 4
        elif delta <= -1.5:
            strength = 3
        else:
            strength = 2
        reason = (
            f"O preço atual está no menor valor observado neste anúncio durante "
            f"o período acompanhado."
        )
    elif delta <= -5:
        label = "Excelente preço"
        strength = 3
        pct = f"{abs(delta):.1f}".replace(".", ",")
        reason = f"O preço atual está {pct}% abaixo da média observada."
    elif delta <= -1.5:
        label = "Bom preço"
        strength = 2
        pct = f"{abs(delta):.1f}".replace(".", ",")
        reason = f"O preço atual está {pct}% abaixo da média observada."
    elif range_pct < 1:
        label = "Preço estável"
        strength = 0
        reason = "O preço variou menos de 1% no período acompanhado."
    elif delta <= 3:
        label = "Preço normal"
        strength = 1
        reason = "O preço atual está próximo da média observada."
    else:
        label = "Acima da média"
        strength = -1
        pct = f"{delta:.1f}".replace(".", ",")
        reason = f"O preço atual está {pct}% acima da média observada."

    return label, strength, reason, delta, range_pct


def main() -> int:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    products = catalog.get("products", [])
    if not isinstance(products, list):
        raise RuntimeError("dados/catalogo.json sem products válido")

    anchor = anchor_time(products)
    remote = os.getenv('MIRA_HISTORY_BASE_URL', '')
    base = history_base(remote) if remote else None
    session = requests.Session() if base else None
    published = set(catalog.get('publishedIds', []))
    by_id: dict[str, dict] = {}
    ranked: list[tuple[float, dict]] = []
    remote_failed = False

    for product in products:
        item_id = str(product.get("id") or "")
        if base and item_id not in published:
            continue
        if (
            product.get("category") not in TECH_CATEGORIES
            or product.get("available") is False
            or not item_id.startswith("MLB")
            or not str(product.get("affiliateUrl") or "").startswith("https://meli.la/")
            or not str(product.get("imageUrl") or "").startswith(("https://", "http://"))
        ):
            continue

        current = finite_price(product.get("price"))
        evidence = product.get("priceCheck") or {}
        checked_at = parse_time(evidence.get("checkedAt"))
        if (
            current is None
            or checked_at is None
            or evidence.get("status") != "verified"
            or evidence.get("price") != product.get("price")
            or anchor - checked_at > timedelta(hours=MAX_PRICE_AGE_HOURS)
        ):
            continue

        try:
            if base:
                response = session.get(base + '/api/history/' + item_id, timeout=(5, 15), allow_redirects=False)
                if response.status_code >= 500 or response.status_code == 429:
                    remote_failed = True
                    break
                if response.status_code != 200:
                    continue
                history = response.json()
                if history.get('productId') != item_id or history.get('currency') != 'BRL':
                    continue
            else:
                history_path = HISTORY / f"{item_id}.json"
                if not history_path.exists():
                    continue
                history = json.loads(history_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, requests.RequestException):
            if base:
                remote_failed = True
                break
            continue

        rows = matching_rows(product, history, anchor)
        if len(rows) < MIN_OBSERVATIONS:
            continue

        span_hours = (rows[-1]["at"] - rows[0]["at"]).total_seconds() / 3600
        if span_hours < MIN_SPAN_HOURS:
            continue

        label, strength, reason, delta, range_pct = classify(current, rows)
        span_days = span_hours / 24
        available_days = max(1, math.ceil(span_days))
        all_values = [row["price"] for row in rows]
        minimum = min(all_values)
        maximum = max(all_values)
        average = sum(all_values) / len(all_values)

        insight = {
            "id": item_id,
            "name": str(product.get("name") or item_id),
            "category": str(product.get("category") or "Tecnologia"),
            "imageUrl": product.get("imageUrl"),
            "affiliateUrl": product.get("affiliateUrl"),
            "currentPrice": round(current, 2),
            "currentPriceText": money(current),
            "averagePrice": round(average, 2),
            "averagePriceText": money(average),
            "minimumPrice": round(minimum, 2),
            "minimumPriceText": money(minimum),
            "maximumPrice": round(maximum, 2),
            "maximumPriceText": money(maximum),
            "deltaAveragePct": round(delta, 2),
            "rangePct": round(range_pct, 2),
            "observations": len(rows),
            "spanDays": round(span_days, 1),
            "periodText": f"{available_days} dias acompanhados",
            "checkedAt": checked_at.isoformat(timespec="seconds"),
            "label": label,
            "strength": strength,
            "reason": reason,
            "actionable": strength >= 2 and span_days >= MIN_ACTIONABLE_SPAN_DAYS,
            "stats30": stats(rows, anchor, 30),
            "stats90": stats(rows, anchor, 90) if span_days >= 30 else None,
            "stats180": stats(rows, anchor, 180) if span_days >= 90 else None,
        }
        by_id[item_id] = insight

        score = (
            strength * 100
            + max(-delta, 0) * 2
            + min(len(rows), 100) / 20
            + min(span_days, 30) / 10
        )
        ranked.append((score, insight))

    if remote_failed:
        print('Radar remoto indisponível; o registro anterior permanece com sua data original.')
        return 0
    featured: list[str] = []
    category_count: dict[str, int] = {}
    for _, item in sorted(ranked, key=lambda pair: pair[0], reverse=True):
        if not item["actionable"]:
            continue
        category = item["category"]
        if category_count.get(category, 0) >= MAX_PER_CATEGORY:
            continue
        featured.append(item["id"])
        category_count[category] = category_count.get(category, 0) + 1
        if len(featured) >= MAX_FEATURED:
            break

    output = {
        "generatedAt": anchor.isoformat(timespec="seconds"),
        "eligibleCount": len(by_id),
        "featuredCount": len(featured),
        "featured": featured,
        "byId": dict(sorted(by_id.items())),
        "methodology": {
            "source": "Observações verificadas do mesmo anúncio e variação",
            "maxPriceAgeHours": MAX_PRICE_AGE_HOURS,
            "historyLimitDays": 180,
            "minimumObservations": MIN_OBSERVATIONS,
            "minimumSpanHours": MIN_SPAN_HOURS,
            "minimumActionableSpanDays": MIN_ACTIONABLE_SPAN_DAYS,
            "note": "Preço de referência da loja não é usado como histórico. Frete e cupons pessoais não entram no cálculo.",
        },
    }

    OUTPUT.parent.mkdir(exist_ok=True)
    content = json.dumps(output, ensure_ascii=False, indent=2) + "\n"
    previous = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
    if previous != content:
        OUTPUT.write_text(content, encoding="utf-8")
        print(f"Radar atualizado: {len(featured)} destaques; {len(by_id)} produtos elegíveis.")
    else:
        print("Radar sem mudanças.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
