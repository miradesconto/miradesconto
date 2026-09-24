'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('analytics.js', 'utf8');
function run(id, consent) {
  const listeners = {};
  const added = [];
  const document = {
    currentScript: {src: 'https://example.org/miradesconto/analytics.js'},
    readyState: 'complete',
    head: {append: node => added.push(node)},
    body: {append: node => added.push(node)},
    createElement: tag => ({tag, children:[], setAttribute() {}, addEventListener(name,cb) {this[name]=cb;}, append(...nodes) {this.children.push(...nodes);}, remove() {}}),
    querySelectorAll: () => [],
    addEventListener: (name, cb) => { (listeners[name] ||= []).push(cb); },
  };
  const window = {
    MIRA_GA4_ID: id,
    location: {href: 'https://example.org/miradesconto/?secret=private',origin:'https://example.org',pathname:'/miradesconto/'},
    dispatchEvent() {},
    MIRA_DATA: {products: [{id: 'MLB123', name: 'Produto exemplo', category: 'Casa', price: 89.9, affiliateUrl: 'https://meli.la/abc'}]},
  };
  vm.runInNewContext(source, {window, document, localStorage: {getItem: () => consent, setItem() {}}, URL, Date, CustomEvent:class {constructor(type,options){this.type=type;this.detail=options.detail;}}});
  return {window, listeners, added};
}
const unconfigured = run('', 'granted');
assert.equal(unconfigured.added.length, 0);
assert.equal(typeof unconfigured.listeners.click[0], 'function');
const denied = run('G-ABCDE12345', 'denied');
assert.equal(denied.added.length, 0);
const accepted = run('G-ABCDE12345', 'granted');
assert.equal(accepted.added[0].src, 'https://www.googletagmanager.com/gtag/js?id=G-ABCDE12345');
const affiliate = {href: 'https://meli.la/abc', textContent: 'Ver oferta', closest: selector => selector === '.hero' ? {} : null};
accepted.listeners.click[0]({target: {closest: selector => selector === 'a[href]' ? affiliate : null}});
const event = accepted.window.dataLayer.at(-1);
assert.equal(event[0], 'event');
assert.equal(event[1], 'affiliate_click');
assert.equal(event[2].item_id, 'MLB123');
assert.equal(event[2].link_location, 'hero');
assert.equal(event[2].item_price, undefined);
assert.equal(JSON.stringify(event).includes('https://meli.la/abc'), false);
const click = {target:{closest:() => affiliate}};
unconfigured.listeners.click[0](click);
assert.equal(unconfigured.window.MiraAnalytics.snapshot()[0].count,1);
assert.equal(unconfigured.window.dataLayer,undefined);
unconfigured.listeners.auxclick[0]({...click,type:'auxclick',button:2});
assert.equal(unconfigured.window.MiraAnalytics.snapshot()[0].count,1);
unconfigured.listeners.auxclick[0]({...click,type:'auxclick',button:1});
assert.equal(unconfigured.window.MiraAnalytics.snapshot()[0].count,2);
unconfigured.window.MiraAnalytics.reset();
assert.equal(unconfigured.window.MiraAnalytics.snapshot().length,0);
denied.listeners.click[0](click);
assert.equal(denied.window.dataLayer,undefined);
assert.equal(JSON.stringify(accepted.window.dataLayer).includes('secret'),false);
accepted.window.MiraAnalytics.openPreferences();
accepted.added.at(-1).children[1].children[1].click();
assert.equal(accepted.window['ga-disable-G-ABCDE12345'],true);
const before=accepted.window.dataLayer.length;
accepted.listeners.click[0](click);
assert.equal(accepted.window.dataLayer.length,before);
console.log('GA4: consentimento, carregamento e clique de afiliado OK');
