import test from 'node:test';
import assert from 'node:assert/strict';
import worker from '../worker.js';
import allowed from '../allowed-items.json' with {type: 'json'};
import destinations from '../affiliate-links.json' with {type: 'json'};
import {affiliateDestination} from '../affiliate-destinations.js';

const id = Object.keys(destinations).find(key => destinations[key].kind === 'tracked_product');
const signed = Object.keys(destinations).find(key => destinations[key].kind === 'signed_link');
const raw = record => record.baseUrl + record.search + record.hash;
const request = (path, init = {}) => worker.fetch(new Request('https://worker.test' + path, init), {
  ALLOWED_ORIGINS: 'https://miradesconto.com.br',
  ML_ACCESS_TOKEN: 'never-expose-this-token',
  PRICE_CACHE: {idFromName() {throw new Error('Compra não deve consultar preços');}}
});

test('todos os destinos registrados são individuais, válidos e correspondem à allowlist de preços', () => {
  assert.deepEqual(Object.keys(destinations).sort(), Object.keys(allowed).sort());
  assert.equal(new Set(Object.values(destinations).map(raw)).size, Object.keys(destinations).length);
  for (const [key, value] of Object.entries(destinations)) assert.equal(affiliateDestination(key), raw(value), key);
});

test('GET retorna 302 com parâmetros e fragmento oficiais sem consultar ML/DO', async () => {
  const response = await request('/go/' + id);
  assert.equal(response.status, 302);
  assert.equal(response.headers.get('Location'), raw(destinations[id]));
  assert.equal(await response.text(), '');
  assert.equal(response.headers.get('Cache-Control'), 'no-store');
  assert.equal(response.headers.get('CDN-Cache-Control'), 'no-store');
  assert.equal(response.headers.get('X-Robots-Tag'), 'noindex, nofollow');
});

test('referência oficial individual, etiqueta e ID de ferramenta permanecem intactos', async () => {
  const response = await request('/go/' + signed);
  assert.equal(response.status, 302);
  const location = response.headers.get('Location');
  assert.equal(location, raw(destinations[signed]));
  const url = new URL(location);
  assert.ok(url.searchParams.get('ref'));
  assert.ok(url.searchParams.get('matt_tool'));
  assert.ok(url.searchParams.get('matt_word'));
  assert.ok(!location.includes('never-expose-this-token'));
});

test('HEAD permite conferir Location sem seguir o destino nem retornar corpo', async () => {
  const response = await request('/go/' + id, {method: 'HEAD'});
  assert.equal(response.status, 302);
  assert.equal(response.headers.get('Location'), raw(destinations[id]));
  assert.equal(await response.text(), '');
});

test('rota aceita navegação de redes sociais, enquanto a API mantém CORS restrito', async () => {
  const headers = {Origin: 'https://social.example'};
  assert.equal((await request('/go/' + id, {headers})).status, 302);
  assert.equal((await request('/api/prices?ids=' + id, {headers})).status, 403);
});

test('IDs desconhecidos retornam 404 sem lista genérica como fallback', async () => {
  const response = await request('/go/MLB0000000000');
  assert.equal(response.status, 404);
  assert.equal(response.headers.get('Location'), null);
  assert.equal(await response.text(), 'ITEM_NOT_REGISTERED');
});

test('IDs e caminhos malformados não redirecionam', async () => {
  for (const path of ['/go', '/go/', '/go/mlb1234567890', '/go/MLB123', '/go/%4dLB1234567890',
    '/go/' + id + '/', '/go/' + id + '/extra', '/go/https://evil.test']) {
    const response = await request(path);
    assert.equal(response.status, 400, path);
    assert.equal(response.headers.get('Location'), null);
  }
});

test('queries de campanha funcionam e visitantes não sobrescrevem o rastreio/destino', async () => {
  for (const query of ['?url=https://evil.test', '?next=https://evil.test', '?tag=attacker',
    '?matt_tool=123', '?utm_source=telegram', '?fbclid=campaign', '?id=' + signed]) {
    const response = await request('/go/' + id + query);
    assert.equal(response.status, 302);
    assert.equal(response.headers.get('Location'), raw(destinations[id]));
  }
});

test('POST e OPTIONS nunca produzem redirect', async () => {
  for (const method of ['POST', 'PUT', 'DELETE', 'OPTIONS']) {
    const response = await request('/go/' + id, {method});
    assert.equal(response.status, 405);
    assert.equal(response.headers.get('Allow'), 'GET, HEAD');
    assert.equal(response.headers.get('Location'), null);
  }
});

test('registro não pode trocar host, credenciais, esquema ou remover rastreio', () => {
  const record = destinations[id];
  for (const baseUrl of ['https://evil.test/p/MLB1234567890',
    'https://www.mercadolivre.com.br.evil.test/p/MLB1234567890',
    record.baseUrl.replace('https://', 'http://'),
    record.baseUrl.replace('https://', 'https://attacker@'),
    record.baseUrl + '?next=evil', record.baseUrl + '\r\nLocation:https://evil.test'])
    assert.equal(affiliateDestination(id, {...record, baseUrl}), null);
  assert.equal(affiliateDestination(id, {...record, search: '', hash: ''}), null);
  assert.equal(affiliateDestination(id, {...record, kind: 'generic_list'}), null);
  assert.equal(affiliateDestination(signed, {...destinations[signed], search: '?matt_tool=123&matt_word=label'}), null);
  assert.equal(affiliateDestination(signed, {...destinations[signed],
    search: destinations[signed].search.replace('matt_tool=29904275', 'matt_tool=12345678')}), null);
  assert.equal(affiliateDestination(id, {...record,
    hash: record.hash.replace('matt_tool_id=29904275', 'matt_tool_id=12345678')}), null);
});

test('anúncio e variação divergentes são recusados mesmo com rastreio válido', () => {
  const record = destinations[id];
  assert.equal(affiliateDestination(id, {...record, variationId: '123'}), null);
  assert.equal(affiliateDestination(id, {...record,
    search: record.search + (record.search ? '&' : '?') + 'wid=MLB0000000000'}), null);
  assert.equal(affiliateDestination(id, {...record,
    search: record.search + (record.search ? '&' : '?') + 'searchVariation=123'}), null);
});
