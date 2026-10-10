import test from 'node:test';
import assert from 'node:assert/strict';
import worker, {PriceCache, POLICY, normalizeItem} from '../worker.js';
import allowed from '../allowed-items.json' with {type: 'json'};

const ids = Object.keys(allowed).filter(id => allowed[id] === null);
const A = ids[0], B = ids[1], C = ids[2];
const BASE = Date.parse('2026-10-09T18:00:00Z');

function harness(t, extraEnv = {}, initial = new Map()) {
  let now = BASE, calls = 0;
  const stored = new Map(initial), pending = new Set();
  t.mock.method(Date, 'now', () => now);
  const state = {
    blockConcurrencyWhile: fn => fn(),
    waitUntil(promise) {pending.add(promise); promise.finally(() => pending.delete(promise));},
    storage: {
      async list() {return new Map([...stored].map(([k,v]) => [k,structuredClone(v)]));},
      async put(key, value) {stored.set(key, structuredClone(value));},
      async delete(key) {stored.delete(key);}
    }
  };
  const env = {ML_ACCESS_TOKEN: 'test-secret-not-real', ML_AUTH_MODE: 'access_token',
    ALLOWED_ORIGINS: 'https://miradesconto.com.br', ...extraEnv};
  let object = new PriceCache(state, env);
  env.PRICE_CACHE = {idFromName(name) {assert.equal(name, 'ml-prices-v1'); return name;},
    get() {return {fetch: (url, init) => object.fetch(new Request(url, init))};}};
  const item = (id, extra = {}) => ({id, currency_id: 'BRL', price: 129.90,
    original_price: 199.90, status: 'active', available_quantity: 10, ...extra});
  let upstream = async url => {
    const queried = new URL(url).searchParams.get('ids').split(',');
    return Response.json(queried.map(id => ({code: 200, body: item(id)})));
  };
  t.mock.method(globalThis, 'fetch', async (url, init) => {
    calls++;
    return upstream(url, init);
  });
  return {env, stored, state, item,
    get calls() {return calls;}, get now() {return now;},
    get object() {return object;},
    advance(ms) {now += ms;},
    setUpstream(fn) {upstream = fn;},
    async drain() {await Promise.all([...pending]);},
    async restart() {object = new PriceCache(state, env); await object.ready;},
    request(query = A, origin = 'https://miradesconto.com.br', method = 'GET') {
      const headers = origin ? {Origin: origin} : {};
      return worker.fetch(new Request('https://worker.example/api/prices?ids=' + query, {method, headers}), env);
    }
  };
}

test('100 acessos simultâneos compartilham uma única consulta de preços', async t => {
  const h = harness(t);
  const responses = await Promise.all(Array.from({length: 100}, () => h.request()));
  await h.drain();
  assert.equal(h.calls, 1);
  for (const response of responses) {
    assert.equal(response.status, 200);
    assert.equal((await response.json()).items[0].data.price, 129.9);
  }
});

test('10 min fresco, SWR imediato por 5 min, sem renovar checkedAt do dado antigo', async t => {
  const h = harness(t);
  const first = (await (await h.request()).json()).items[0];
  assert.equal(first.cache, 'MISS');
  h.advance(599999);
  assert.equal((await (await h.request()).json()).items[0].cache, 'HIT');
  assert.equal(h.calls, 1);
  h.advance(2);
  let finish;
  const gate = new Promise(resolve => {finish = resolve;});
  h.setUpstream(async () => {await gate; return Response.json([{code: 200, body: h.item(A, {price: 119})}]);});
  const stale = (await (await h.request()).json()).items[0];
  assert.equal(stale.cache, 'STALE');
  assert.equal(stale.data.checkedAt, first.data.checkedAt);
  await h.request();
  assert.equal(h.calls, 2);
  finish(); await h.drain();
  const refreshed = (await (await h.request()).json()).items[0];
  assert.equal(refreshed.data.price, 119);
  assert.notEqual(refreshed.data.checkedAt, first.data.checkedAt);
});

test('lotes sobrepostos não duplicam um anúncio, nem a ordem muda a chave', async t => {
  const h = harness(t);
  await Promise.all([h.request(A+','+B), h.request(B+','+C), h.request(B+','+A)]);
  await h.drain();
  assert.equal(h.calls, 2);
  await h.request(C+','+B+','+A);
  assert.equal(h.calls, 2);
});

test('cache positivo sobrevive ao reinício do Durable Object', async t => {
  const h = harness(t);
  await h.request(); await h.drain(); await h.restart();
  assert.equal((await (await h.request()).json()).items[0].cache, 'HIT');
  assert.equal(h.calls, 1);
});

test('403 mantém o último dado somente até 15 min; cooldown não martela a API', async t => {
  const h = harness(t);
  const old = (await (await h.request()).json()).items[0].data;
  h.advance(600001);
  h.setUpstream(async () => new Response('forbidden test-secret-not-real', {status: 403}));
  const stale = (await (await h.request()).json()).items[0];
  assert.equal(stale.data.checkedAt, old.checkedAt);
  await h.drain();
  await Promise.all(Array.from({length: 25}, () => h.request()));
  assert.equal(h.calls, 2);
  h.advance(300000);
  const expired = (await (await h.request()).json()).items[0];
  assert.equal(expired.cache, 'ERROR'); assert.equal(expired.code, 403);
  assert.equal(expired.data, undefined);
  assert.equal(h.stored.get('price:' + A).data.checkedAt, old.checkedAt);
  assert.ok(!JSON.stringify(expired).includes('test-secret-not-real'));
});

test('429 respeita Retry-After global, inclusive para outro produto e após reinício', async t => {
  const h = harness(t);
  h.setUpstream(async () => new Response('', {status: 429, headers: {'Retry-After': '120'}}));
  const result = (await (await h.request()).json()).items[0];
  assert.equal(result.error.retryAfterSeconds, 120);
  await h.restart(); await h.request(B);
  assert.equal(h.calls, 1);
  h.advance(120001); await h.request(B);
  assert.equal(h.calls, 2);
});

test('429 dentro de multiget também aciona a pausa global', async t => {
  const h = harness(t);
  h.setUpstream(async () => Response.json([{code: 429, body: {}}]));
  await h.request(); await h.drain(); await h.request(B);
  assert.equal(h.calls, 1);
});

test('401 com token fixo não faz retry cego nem expõe credenciais', async t => {
  const h = harness(t);
  h.setUpstream(async () => new Response('test-secret-not-real', {status: 401}));
  const result = (await (await h.request()).json()).items[0];
  assert.equal(result.code, 401); assert.equal(h.calls, 1);
  assert.ok(!JSON.stringify(result).includes('test-secret-not-real'));
});

test('redirect da origem é recusado sem enviar Bearer para outro host', async t => {
  const h = harness(t);
  h.setUpstream(async (url, init) => {
    assert.equal(init.redirect, 'manual');
    return new Response('', {status: 302, headers: {Location: 'https://evil.example'}});
  });
  const result = (await (await h.request()).json()).items[0];
  assert.equal(result.error.code, 'ML_UNEXPECTED_REDIRECT'); assert.equal(h.calls, 1);
});

test('CORS, método, allowlist, quantidade e queries são validados antes do ML', async t => {
  const h = harness(t);
  assert.equal((await h.request(A, 'https://evil.example')).status, 403);
  assert.equal((await h.request(A, null, 'POST')).status, 405);
  for (const query of ['bad', 'MLB1234567', A+'&url=https://evil.example', A+'&ids='+A,
    Array.from({length: 21}, () => A).join(',')]) assert.equal((await h.request(query)).status, 400);
  assert.equal(h.calls, 0);
  const ok = await h.request();
  assert.equal(ok.headers.get('Access-Control-Allow-Origin'), 'https://miradesconto.com.br');
  assert.equal(ok.headers.get('Cache-Control'), 'no-store');
  assert.equal(ok.headers.get('Vary'), 'Origin');
  assert.equal((await h.request(A, 'https://miradesconto.com.br', 'OPTIONS')).status, 204);
});

test('moeda, anúncio e preço inválidos não viram evidência nem sobrescrevem cache', async t => {
  const h = harness(t);
  const stamp = new Date(BASE).toISOString();
  for (const extra of [{id: B}, {currency_id: 'USD'}, {price: '100'}, {price: NaN}, {price: 0}])
    assert.throws(() => normalizeItem(h.item(A, extra), A, stamp));
  await h.request(); await h.drain(); h.advance(900000);
  h.setUpstream(async () => Response.json([{code: 200, body: h.item(A, {currency_id: 'USD'})}]));
  assert.equal((await (await h.request()).json()).items[0].cache, 'ERROR');
  assert.equal(h.stored.get('price:' + A).data.checkedAt, stamp);
});

test('variação exata é exigida e seu desconto de referência não é inferido', async t => {
  const h = harness(t), variantId = Object.keys(allowed).find(id => allowed[id] !== null);
  const body = h.item(variantId, {variations: [{id: allowed[variantId], price: 99}]});
  const data = normalizeItem(body, variantId, new Date(BASE).toISOString());
  assert.equal(data.price, 99); assert.equal(data.oldPrice, null);
  assert.throws(() => normalizeItem({...body, variations: [{id: '99999', price: 1}]}, variantId, data.checkedAt));
});

test('item pausado/sem quantidade disponível não vira oferta ativa', async t => {
  const h = harness(t), stamp = new Date(BASE).toISOString();
  assert.equal(normalizeItem(h.item(A, {status: 'paused'}), A, stamp).available, false);
  assert.equal(normalizeItem(h.item(A, {available_quantity: 0}), A, stamp).available, false);
});

test('lote parcialmente falho preserva o produto que respondeu corretamente', async t => {
  const h = harness(t);
  h.setUpstream(async url => Response.json(new URL(url).searchParams.get('ids').split(',').map(id =>
    id === A ? {code: 200, body: h.item(id)} : {code: 404, body: {}})));
  const items = (await (await h.request(A+','+B)).json()).items;
  assert.equal(items.find(p => p.id === A).code, 200); assert.equal(items.find(p => p.id === B).code, 404);
});

test('OAuth renova uma vez, persiste rotação e reutiliza o token após reinício', async t => {
  const h = harness(t, {ML_AUTH_MODE: 'oauth', ML_AUTH_SEED_VERSION: '1',
    ML_CLIENT_ID: 'test-client', ML_CLIENT_SECRET: 'test-secret', ML_REFRESH_TOKEN: 'test-refresh'});
  let refreshes = 0;
  h.setUpstream(async (url, init) => {
    if (url.endsWith('/oauth/token')) {
      refreshes++;
      assert.equal(h.stored.get('oauth').blocked, true);
      assert.equal(init.body.get('refresh_token'), 'test-refresh');
      return Response.json({access_token: 'new-access', refresh_token: 'new-refresh', expires_in: 21600});
    }
    assert.equal(init.headers.Authorization, 'Bearer new-access');
    return Response.json(new URL(url).searchParams.get('ids').split(',').map(id => ({code: 200, body: h.item(id)})));
  });
  const replies = await Promise.all([h.request(A), h.request(B)]); await h.drain();
  for (const reply of replies) assert.equal((await reply.json()).items[0].code, 200);
  assert.equal(refreshes, 1); assert.equal(h.stored.get('oauth').refreshToken, 'new-refresh');
  await h.restart(); await h.request(C);
  assert.equal(refreshes, 1);
});

test('OAuth POST incerto bloqueia replay de refresh mesmo após reinício', async t => {
  const h = harness(t, {ML_AUTH_MODE: 'oauth', ML_CLIENT_ID: 'test-client',
    ML_CLIENT_SECRET: 'test-secret', ML_REFRESH_TOKEN: 'test-refresh'});
  h.setUpstream(async () => {throw new Error('network dropped');});
  await h.request(); await h.drain(); await h.restart(); h.advance(300001);
  const result = (await (await h.request(B)).json()).items[0];
  assert.equal(result.error.code, 'ML_OAUTH_REAUTHORIZE'); assert.equal(h.calls, 1);
});

test('nova semente OAuth recupera estado bloqueado sem reutilizar token consumido', async t => {
  const h = harness(t, {ML_AUTH_MODE: 'oauth', ML_CLIENT_ID: 'client', ML_CLIENT_SECRET: 'secret',
    ML_REFRESH_TOKEN: 'new-seed', ML_AUTH_SEED_VERSION: '2'},
    new Map([['oauth', {seedVersion: '1', blocked: true}]]));
  h.setUpstream(async url => url.endsWith('/oauth/token')
    ? Response.json({access_token: 'access', refresh_token: 'rotated', expires_in: 21600})
    : Response.json([{code: 200, body: h.item(A)}]));
  assert.equal((await (await h.request()).json()).items[0].code, 200);
  assert.equal(h.stored.get('oauth').seedVersion, '2');
});
