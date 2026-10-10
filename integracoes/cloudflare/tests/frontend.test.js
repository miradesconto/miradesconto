import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import fs from 'node:fs';
import {createRequire} from 'node:module';
const require = createRequire(import.meta.url);
const {usablePrice} = require('../../../qualidade.js');
const client = fs.readFileSync(new URL('../../../precos.js', import.meta.url), 'utf8');
const NOW = Date.now();
const id = 'MLB4408547152';

function fixture() {
  return {id, itemId: id, price: 4000, oldPrice: 5000, available: null,
    affiliateUrl: 'https://meli.la/original', offerUrl: 'https://www.mercadolivre.com.br/original',
    priceCheck: {method: 'poly-card-v1', status: 'verified', itemId: id, variationId: null,
      currency: 'BRL', checkedAt: new Date(NOW - 7200000).toISOString(), price: 4000, oldPrice: 5000}};
}
function data(extra = {}) {
  return {id, itemId: id, method: 'ml-edge-item-v1', variationId: null, currency: 'BRL',
    price: 3900, oldPrice: 5000, available: null, availabilityStatus: 'unknown',
    checkedAt: new Date(NOW - 1000).toISOString(), ...extra};
}
function context(payload, base = 'https://worker.example', responseCode = 200) {
  let calls = 0, events = 0, urls = [];
  const window = {MIRA_PRICE_CONFIG: {apiBaseUrl: base}, dispatchEvent() {events++;}};
  vm.runInNewContext(client, {window, document: {hidden: false}, URL, Date, Map, Set, Object,
    AbortController, setTimeout, clearTimeout, Event, Error,
    async fetch(url) {calls++; urls.push(url); return {ok: responseCode === 200, status: responseCode, json: async () => payload};}});
  return {prices: window.MiraPrices, get calls() {return calls;}, get events() {return events;}, urls};
}

test('cliente usa somente o Worker, aceita evidência válida e preserva links', async () => {
  const p = fixture(), h = context({items: [{id, code: 200, cache: 'MISS', data: data()}]});
  await h.prices.refresh([p]);
  assert.equal(p.price, 3900); assert.equal(p.priceCheck.method, 'ml-edge-item-v1');
  assert.equal(p.affiliateUrl, 'https://meli.la/original');
  assert.equal(p.offerUrl, 'https://www.mercadolivre.com.br/original');
  assert.ok(h.urls[0].startsWith('https://worker.example/api/prices?ids='));
  assert.equal(usablePrice(p, NOW), true);
});

test('cache coalescido no navegador impede duplicações após render/eventos', async () => {
  const p = fixture(), h = context({items: [{id, code: 200, cache: 'HIT', data: data()}]});
  await Promise.all([h.prices.refresh([p]), h.prices.refresh([p])]);
  await h.prices.refresh([p]); assert.equal(h.calls, 1);
});

test('403 preserva preço, referência e checkedAt sem promover dado a verificado', async () => {
  const p = fixture(), previous = JSON.stringify(p.priceCheck);
  const h = context({items: [{id, code: 403, error: {code: 'ML_HTTP_403', retryAfterSeconds: 300}}]});
  await h.prices.refresh([p]);
  assert.equal(p.price, 4000); assert.equal(p.oldPrice, 5000);
  assert.equal(JSON.stringify(p.priceCheck), previous); assert.equal(usablePrice(p, NOW), false);
  assert.equal(p.edgePrice.status, 'error');
});

test('anúncio, moeda, idade e variação divergentes não alteram o produto', async () => {
  for (const change of [{id:'MLB0000000000'}, {currency:'USD'}, {price:'1'},
    {variationId:'123'}, {checkedAt: new Date(NOW - 1000000).toISOString()}]) {
    const p = fixture(), h = context({items: [{id, code: 200, data: data(change)}]});
    await h.prices.refresh([p]); assert.equal(p.price, 4000); assert.equal(p.edgePrice.status, 'error');
  }
});

test('indisponibilidade não reutiliza a promoção como oferta ativa', async () => {
  const p = fixture(), h = context({items: [{id, code: 200, data: data({available:false, price:null})}]});
  await h.prices.refresh([p]); assert.equal(p.available, false); assert.equal(usablePrice(p, NOW), false);
});

test('evidência Edge vence em 15 minutos, sem prolongar pela idade do browser', () => {
  const p = {...fixture(), ...data()};
  p.priceCheck = {status:'verified', method:'ml-edge-item-v1', itemId:id, currency:'BRL',
    price:p.price, oldPrice:p.oldPrice, checkedAt:new Date(NOW).toISOString()};
  assert.equal(usablePrice(p,NOW+899999), true); assert.equal(usablePrice(p,NOW+900000), false);
});

test('configuração vazia ou HTTP externo mantém o modo estático sem request', async () => {
  for (const base of ['', 'http://evil.example']) {
    const h = context({}, base); assert.equal(h.prices.enabled, false);
    await h.prices.refresh([fixture()]); assert.equal(h.calls, 0);
  }
});

test('Worker fora do ar mantém valores e marca falha no cliente', async () => {
  const p = fixture(), h = context({}, 'https://worker.example', 503);
  await h.prices.refresh([p]); assert.equal(p.price, 4000); assert.equal(p.edgePrice.status, 'error');
});
