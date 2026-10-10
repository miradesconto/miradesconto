import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import fs from 'node:fs';

const code = fs.readFileSync(new URL('../../../links.js', import.meta.url), 'utf8');
const analytics = fs.readFileSync(new URL('../../../analytics.js', import.meta.url), 'utf8');
const id = 'MLB4408547152';
function context(base, consent = 'granted') {
  const listeners = {}, scripts = [];
  const product = {id, itemId: id, name: 'Produto', category: 'Celulares', price: 4000,
    affiliateUrl: 'https://meli.la/original'};
  const window = {MIRA_LINK_CONFIG: {goBaseUrl: base}, MIRA_GA4_ID: 'G-ABCDE12345',
    MIRA_DATA: {products: [product]}, location: {href: 'https://miradesconto.com.br/', pathname: '/'}};
  const document = {currentScript: {src: 'https://miradesconto.com.br/analytics.js'}, readyState: 'complete',
    head: {append(node) {scripts.push(node);}}, createElement() {return {};},
    addEventListener(name, callback) {(listeners[name] ||= []).push(callback);}};
  const sandbox = {window, document, URL, Set, Object,
    localStorage: {getItem() {return consent;}}};
  vm.runInNewContext(code, sandbox);
  vm.runInNewContext(analytics, sandbox);
  function click(href) {
    const link = {href, textContent: 'Ver produto', dataset: {itemId: id, destinationType: 'product'},
      closest(selector) {return selector === '.hero' ? {} : null;}};
    listeners.click[0]({target: {closest() {return link;}}});
  }
  return {window, links: window.MiraLinks, product, scripts, click};
}

test('botão ganha apenas /go/ID, sem link original, tag ou preço na URL', () => {
  const h = context('https://worker.example');
  assert.equal(h.links.enabled, true);
  assert.equal(h.links.forProduct(h.product), 'https://worker.example/go/' + id);
  assert.equal(h.product.affiliateUrl, 'https://meli.la/original');
});

test('configuração vazia mantém os links existentes até a implantação', () => {
  const h = context('');
  assert.equal(h.links.enabled, false);
  assert.equal(h.links.forProduct(h.product), null);
  assert.equal(h.links.isGoLink('https://miradesconto.com.br/go/' + id), false);
});

test('configurações inválidas não criam rota incorreta ou insegura', () => {
  for (const base of ['http://worker.example', 'javascript:alert(1)', 'https://user:pass@worker.example',
    'https://worker.example/go', 'https://worker.example/?tag=x', 'https://worker.example/#x'])
    assert.equal(context(base).links.enabled, false, base);
});

test('mesmo domínio e localhost usam o prefixo /go exato', () => {
  const local = context('http://localhost:8787');
  assert.equal(local.links.forProduct(local.product), 'http://localhost:8787/go/' + id);
  const same = context('https://miradesconto.com.br');
  assert.equal(same.links.forProduct(same.product), 'https://miradesconto.com.br/go/' + id);
});

test('IDs não publicados e identidade divergente não geram links de compra', () => {
  const h = context('https://worker.example');
  for (const p of [null, {id: 'MLB123'}, {id: 'MLB0000000000'}, {...h.product, itemId: 'MLB0000000000'}])
    assert.equal(h.links.forProduct(p), null);
});

test('analytics reconhece somente /go publicado na origem configurada', () => {
  const h = context('https://worker.example');
  assert.equal(h.links.isGoLink('https://worker.example/go/' + id), true);
  for (const href of ['https://evil.example/go/' + id, 'https://worker.example/go/MLB0000000000',
    'https://worker.example/go/' + id + '?url=evil', 'https://worker.example/go/' + id + '#x',
    'https://user@worker.example/go/' + id]) assert.equal(h.links.isGoLink(href), false);
});

test('clique no link curto mantém item_id e evento com consentimento, sem divulgar URL completa', () => {
  const h = context('https://worker.example');
  h.click(h.links.forProduct(h.product));
  const event = h.window.dataLayer.at(-1);
  assert.equal(event[1], 'affiliate_click');
  assert.equal(event[2].item_id, id);
  assert.equal(event[2].destination_type, 'product');
  assert.equal(event[2].affiliate_host, 'worker.example');
  assert.equal(event[2].link_location, 'hero');
  assert.equal(JSON.stringify(event).includes('/go/'), false);
});

test('links curtos não ativam analytics após recusa de consentimento', () => {
  const h = context('https://worker.example', 'denied');
  h.click(h.links.forProduct(h.product));
  assert.equal(h.window.dataLayer, undefined);
  assert.equal(h.scripts.length, 0);
});

test('link /go de outra origem não dispara evento de afiliado', () => {
  const h = context('https://worker.example');
  const before = h.window.dataLayer.length;
  h.click('https://evil.example/go/' + id);
  assert.equal(h.window.dataLayer.length, before);
});
