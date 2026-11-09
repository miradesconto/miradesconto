'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

// A renderização Liquid é validada pelo build Jekyll no workflow.
const markup = fs.readFileSync('_includes/vitrine-card.html', 'utf8');
const style = fs.readFileSync('vitrine.css', 'utf8');
assert.match(markup, /titulo \| truncate: 55/);
assert.match(markup, /offer\.price != blank/);
assert.match(markup, /product\.price != blank/);
assert.match(markup, /p\.currentPrice != blank/);
assert.match(markup, /Em Oferta!/);
assert.match(markup, /data-specs/);
assert.match(markup, /Ver Oferta/);
assert.match(markup, /data-link-location="daily-showcase"/);
assert.match(style, /min-height:48px/);

function element() {
  return {
    textContent: '', title: '', src: '', alt: '', href: '', hidden: false, children: [],
    dataset: {}, attributes: {},
    classList: {removed: [], remove(name) { this.removed.push(name); }},
    setAttribute(name, value) { this.attributes[name] = value; },
    replaceChildren(...children) { this.children = children; }
  };
}
const fields = new Map([
  ['.vitrine-photo img', element()],
  ['h3', element()],
  ['.vitrine-category', element()],
  ['[data-specs]', element()],
  ['[data-price]', element()],
  ['[data-old]', element()],
  ['[data-hot]', element()],
  ['[data-checked]', element()],
  ['.vitrine-cta', element()]
]);
const section = {hidden:false};
const card = {
  dataset: {vitrineId:'MLB-A', locale:'pt'},
  hidden: false,
  querySelector(selector) {
    assert.ok(fields.has(selector), 'Selector unexpected: ' + selector);
    return fields.get(selector);
  },
  closest(selector) { return selector === '.vitrine-diaria' ? section : null; }
};
const events = {};
const document = {
  querySelectorAll: selector => selector === '[data-vitrine-id]' ? [card] : [],
  createElement: () => element(),
  addEventListener: (type, fn) => {events[type] = fn;},
  dispatchEvent: () => {}
};
const valid = {
  id: 'MLB-A',
  name: 'Notebook AMD Ryzen 5 7520U 16GB RAM 512GB SSD com Windows e Tela Full HD',
  imageUrl: 'https://example.test/notebook.webp',
  affiliateUrl: 'https://meli.la/Alpha123',
  category: 'Notebooks',
  price: 2900,
  oldPrice: 3500,
  priceCheck: {checkedAt: '2026-11-09T18:00:00Z'}
};
const rotated = {
  id: 'MLB-B',
  name: 'Monitor 4K 144Hz IPS com conexões HDMI e DisplayPort para jogos',
  imageUrl: 'https://example.test/monitor.webp',
  affiliateUrl: 'https://meli.la/Beta456',
  category: 'Monitores',
  specs: ['Painel IPS','144Hz','4K','HDMI'],
  price: 1200,
  oldPrice: 1100,
  priceCheck: {checkedAt: '2026-11-09T18:00:00Z'}
};
const window = {MIRA_DATA:{products:[valid]},MiraQuality:{usablePrice:()=>true}};
vm.runInNewContext(fs.readFileSync('vitrine.js','utf8'), {
  window, document, Intl, Date, setInterval:()=>{},
  CustomEvent:class { constructor(type) { this.type = type; } }
});

assert.equal(card.hidden,false);
assert.ok(fields.get('h3').textContent.length <= 55, 'Título dinâmico acima de 55 caracteres');
assert.equal(fields.get('[data-specs]').children.length,3);
assert.deepEqual(fields.get('[data-specs]').children.map(x=>x.textContent),['Ryzen 5','16GB RAM','512GB SSD']);
assert.equal(fields.get('[data-price]').textContent,'R$ 2.900,00');
assert.equal(fields.get('.vitrine-cta').href,valid.affiliateUrl);
assert.equal(fields.get('.vitrine-cta').dataset.itemId,valid.id);
assert.equal(fields.get('.vitrine-cta').attributes['aria-label'],'Ver oferta: '+valid.name);

window.MIRA_DATA.products = [rotated];
events['mira:catalog-updated']();
assert.equal(card.dataset.vitrineId,rotated.id,'Rotação não atualizou produto');
assert.ok(fields.get('h3').textContent.length <= 55);
assert.deepEqual(fields.get('[data-specs]').children.map(x=>x.textContent),['Painel IPS','144Hz','4K']);
assert.equal(fields.get('.vitrine-cta').href,rotated.affiliateUrl);
assert.equal(fields.get('.vitrine-cta').dataset.itemId,rotated.id);
assert.equal(fields.get('.vitrine-cta').attributes['aria-label'],'Ver oferta: '+rotated.name);
assert.equal(fields.get('[data-old]').hidden,true,'Não riscar preço maior que o atual');

window.MIRA_DATA.products = [{...rotated,affiliateUrl:'https://meli.la/1NguveN'}];
events['mira:catalog-updated']();
assert.equal(card.hidden,true,'Link inválido deve ocultar o card');
assert.equal(section.hidden,true,'Seção sem ofertas deve ser ocultada');

console.log('OK: CTA, preço, título, specs, rotação, rastreamento e bloqueio de links.');
