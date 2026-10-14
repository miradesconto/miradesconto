'use strict';
const assert = require('node:assert/strict');
const policy = require('../admin/ofertas.js');

const NOW = Date.parse('2026-10-14T22:00:00Z');
const original = {
  id: 'MLB1234567890',
  itemId: 'MLB1234567890',
  affiliateUrl: 'https://meli.la/abcDEF123',
  price: 100,
  oldPrice: 140,
  available: null,
  priceCheck: {
    status: 'verified', method: 'poly-card-v1',
    itemId: 'MLB1234567890', currency: 'BRL',
    price: 100, oldPrice: 140, checkedAt: '2026-10-14T21:30:00Z'
  }
};
const insight = {
  id: original.id,
  affiliateUrl: original.affiliateUrl,
  currentPrice: 100, deltaAveragePct: -7.5, strength: 3,
  observations: 12, spanDays: 10, actionable: true,
  checkedAt: '2026-10-14T21:30:00Z'
};
const copy = (changed = {}) => ({...original, ...changed, priceCheck: {
  ...original.priceCheck, ...(changed.priceCheck || {})}});
assert.equal(policy.MAX_AGE_MS, 7200000);
assert.equal(policy.priceEvidence(original, NOW).price, 100);
assert.equal(policy.storeReference(original, NOW), 140);
assert.equal(policy.priceEvidence(original, NOW + 3 * 60 * 60 * 1000), null);
assert.equal(policy.priceEvidence(copy({priceCheck:{checkedAt:'2026-10-14T23:00:00Z'}}),NOW),null);
assert.equal(policy.priceEvidence(copy({priceCheck:{checkedAt:'2026-10-14T21:30:00'}}),NOW),null);
assert.equal(policy.priceEvidence(copy({priceCheck:{itemId:'MLB9999999999'}}),NOW),null);
assert.equal(policy.priceEvidence(copy({priceCheck:{method:'unknown'}}),NOW),null);
assert.equal(policy.priceEvidence(copy({priceCheck:{oldPrice:900}}),NOW),null);
assert.equal(policy.priceEvidence(copy({price:NaN}),NOW),null);
assert.equal(policy.priceEvidence(copy({available:false}),NOW),null);
assert.ok(policy.historicalOffer(original, insight, NOW));
assert.equal(policy.historicalOffer(original, {...insight, id:'MLB9999999999'}, NOW),null);
assert.equal(policy.historicalOffer(original, {...insight, affiliateUrl:'https://meli.la/other'}, NOW),null);
assert.equal(policy.historicalOffer(original, {...insight, currentPrice:98}, NOW),null);
assert.equal(policy.historicalOffer(original, {...insight, observations:5}, NOW),null);
assert.equal(policy.historicalOffer(original, {...insight, spanDays:6.9}, NOW),null);
assert.equal(policy.historicalOffer(original, {...insight, actionable:false}, NOW),null);
assert.equal(policy.historicalOffer(original, {...insight, deltaAveragePct:1}, NOW),null);
assert.equal(policy.historicalOffer(original, {...insight, checkedAt:'2026-10-13T21:30:00Z'}, NOW),null);
assert.equal(policy.historicalOffer(copy({affiliateUrl:'https://example.com/ref'}), {...insight,affiliateUrl:'https://example.com/ref'}, NOW),null);
const sale = copy({itemId:'MLB5678901234', priceCheck:{
  method:'ml-sale-price-v1', itemId:'MLB5678901234'
}});
assert.ok(policy.priceEvidence(sale,NOW), 'API buy box must use listing item ID');
assert.equal(policy.priceEvidence(copy({itemId:'MLB5678901234',priceCheck:{
  method:'ml-sale-price-v1', itemId:original.id
}}),NOW),null);
assert.equal(policy.rankedHistoricalOffers([original],{[original.id]:insight},NOW).length,1);
assert.equal(policy.rankedHistoricalOffers([original],{[original.id]:insight},NOW+3*60*60*1000).length,0);
console.log('OK: evidência recente, associação exata e oportunidades com histórico');
