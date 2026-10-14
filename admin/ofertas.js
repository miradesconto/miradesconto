'use strict';
// Critérios compartilhados do painel. Não faz requisições nem altera o catálogo.
(function (root, makePolicy) {
  const policy = makePolicy();
  if (typeof module !== 'undefined' && module.exports) module.exports = policy;
  if (root) root.MiraOfferPolicy = policy;
})(typeof window === 'undefined' ? null : window, function () {
  const MAX_AGE_MS = 2 * 60 * 60 * 1000;
  const MIN_HISTORICAL_OBSERVATIONS = 6;
  const MIN_HISTORICAL_DAYS = 7;
  const VALID_METHODS = new Set(['poly-card-v1', 'ml-sale-price-v1']);
  const TZ = /(Z|[+-]\d{2}:\d{2})$/;

  function amount(value) {
    return typeof value === 'number' && !Number.isNaN(value) &&
      Number.isFinite(value) && value > 0;
  }

  function timestamp(value, now = Date.now()) {
    if (typeof value !== 'string' || !TZ.test(value)) return null;
    const at = Date.parse(value);
    if (!Number.isFinite(at) || at > now || now - at > MAX_AGE_MS) return null;
    return at;
  }

  function sameNullablePrice(left, right) {
    if (left == null || right == null) return left == null && right == null;
    return amount(left) && amount(right) && Math.abs(left - right) < 0.011;
  }

  function priceEvidence(item, now = Date.now()) {
    if (!item || item.available === false) return null;
    const proof = item.priceCheck;
    if (!proof || proof.status !== 'verified' ||
      !VALID_METHODS.has(proof.method) || proof.currency !== 'BRL') return null;
    const expected = proof.method === 'ml-sale-price-v1' ? item.itemId : item.id;
    if (!expected || proof.itemId !== expected || !amount(item.price) ||
        !sameNullablePrice(proof.price, item.price) ||
        !sameNullablePrice(proof.oldPrice, item.oldPrice)) return null;
    const time = timestamp(proof.checkedAt, now);
    if (time === null) return null;
    return { time, price: item.price };
  }

  function storeReference(item, now = Date.now()) {
    const proof = priceEvidence(item, now);
    return proof && amount(item.oldPrice) && item.oldPrice > proof.price
      ? item.oldPrice : null;
  }

  // An actionable Radar candidate must agree with the exact current catalog
  // product, affiliate URL and price, not just claim a promotional badge.
  function historicalOffer(item, radar, now = Date.now()) {
    const evidence = priceEvidence(item, now);
    if (!evidence || !radar || radar.id !== item.id ||
        typeof item.affiliateUrl !== 'string' ||
        !/^https:\/\/(?:meli\.la\/[A-Za-z0-9]+|(?:www\.)?mercadolivre\.com(?:\.br)?\/sec\/[A-Za-z0-9]+)$/.test(item.affiliateUrl) ||
        radar.affiliateUrl !== item.affiliateUrl ||
        radar.actionable !== true || !(radar.strength >= 2) ||
        !(radar.observations >= MIN_HISTORICAL_OBSERVATIONS) ||
        !(radar.spanDays >= MIN_HISTORICAL_DAYS) ||
        !Number.isFinite(radar.deltaAveragePct) || radar.deltaAveragePct > -1.5 ||
        !sameNullablePrice(radar.currentPrice, item.price) ||
        timestamp(radar.checkedAt, now) === null) return null;
    return { item, insight: radar, time: evidence.time };
  }

  function rankedHistoricalOffers(products, byId, now = Date.now()) {
    if (!byId || typeof byId !== 'object') return [];
    return products
      .map(item => historicalOffer(item, byId[item.id], now))
      .filter(Boolean)
      .sort((a, b) =>
        a.insight.deltaAveragePct - b.insight.deltaAveragePct ||
        b.time - a.time || a.item.id.localeCompare(b.item.id));
  }

  return { MAX_AGE_MS, priceEvidence, storeReference, historicalOffer, rankedHistoricalOffers };
});
