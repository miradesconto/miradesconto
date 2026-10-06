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
    createElement: tag => ({tag, setAttribute() {}, addEventListener() {}, append() {}, remove() {}}),
    addEventListener: (name, cb) => { (listeners[name] ||= []).push(cb); },
  };
  const window = {
    MIRA_GA4_ID: id,
    location: {href: 'https://example.org/miradesconto/'},
    MIRA_DATA: {products: [{id: 'MLB123', name: 'Produto exemplo', category: 'Casa', price: 89.9, affiliateUrl: 'https://meli.la/abc'}]},
  };
  vm.runInNewContext(source, {window, document, localStorage: {getItem: () => consent, setItem() {}}, URL, Date});
  return {window, listeners, added};
}
const unconfigured = run('', 'granted');
assert.equal(unconfigured.added.length, 0);
assert.equal(unconfigured.listeners.click, undefined);
const denied = run('G-ABCDE12345', 'denied');
assert.equal(denied.added.length, 0);
const accepted = run('G-ABCDE12345', 'granted');
assert.equal(accepted.added[0].src, 'https://www.googletagmanager.com/gtag/js?id=G-ABCDE12345');
const affiliate = {href: 'https://meli.la/abc', textContent: 'Ver oferta', dataset: {}, closest: selector => selector === '.hero' ? {} : null};
accepted.listeners.click[0]({target: {closest: selector => selector === 'a[href]' ? affiliate : null}});
const event = accepted.window.dataLayer.at(-1);
assert.equal(event[0], 'event');
assert.equal(event[1], 'affiliate_click');
assert.equal(event[2].item_id, 'MLB123');
assert.equal(event[2].link_location, 'hero');
assert.equal(event[2].item_price, 89.9);
assert.equal(JSON.stringify(event).includes('https://meli.la/abc'), false);
console.log('GA4: consentimento, carregamento e clique de afiliado OK');
const direct = {href:'https://www.mercadolivre.com.br/notebook/p/MLB123#source=affiliate-profile&matt_tool_id=29904275&wid=MLB456',textContent:'Ver produto',dataset:{itemId:'MLB456',destinationType:'product'},closest:()=>null};
accepted.listeners.click[0]({target:{closest:()=>direct}});
assert.equal(accepted.window.dataLayer.at(-1)[2].item_id,'MLB456');
assert.equal(accepted.window.dataLayer.at(-1)[2].destination_type,'product');
{
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const code=fs.readFileSync('analytics.js','utf8');
function setup(consent) {
 const listeners={}, scripts=[];
 const document={currentScript:{src:'https://example.org/miradesconto/analytics.js'},readyState:'loading',head:{append:s=>scripts.push(s)},createElement:()=>({}),addEventListener:(name,fn)=>{(listeners[name]??=[]).push(fn);}};
 const window={MIRA_GA4_ID:'G-123456',location:{href:'https://example.org/miradesconto/notebooks/',pathname:'/miradesconto/notebooks/'},MIRA_DATA:{products:[{id:'A',name:'First',affiliateUrl:'https://meli.la/list'},{id:'B',name:'Second',category:'Notebooks',affiliateUrl:'https://meli.la/list'}]}};
 vm.runInNewContext(code,{window,document,localStorage:{getItem:()=>consent},URL});
 function click(dataset={}){const link={href:'https://meli.la/list',textContent:'Abrir lista',dataset,closest:()=>null};listeners.click[0]({target:{closest:()=>link}});}
 return {window,click,scripts};
}
const denied=setup('denied'); denied.click({itemId:'B'});assert.equal(denied.scripts.length,0);assert.equal(denied.window.dataLayer,undefined);
const granted=setup('granted');granted.click({itemId:'B',itemName:'Second',linkLocation:'purchase_page',destinationType:'affiliate_list'});
const event=granted.window.dataLayer.at(-1);assert.equal(event[1],'affiliate_click');assert.equal(event[2].item_id,'B');assert.equal(event[2].item_name,'Second');assert.equal(event[2].destination_type,'affiliate_list');assert.equal(event[2].link_location,'purchase_page');
granted.click();assert.equal(granted.window.dataLayer.at(-1)[2].item_id,undefined,'Ambiguous shared links must not identify the first product');
granted.click({itemId:'OUTSIDE',itemName:'Editorial product'});assert.equal(granted.window.dataLayer.at(-1)[2].item_id,'OUTSIDE');
console.log('OK: consent, exact product attribution, editorial metadata and shared affiliate links');

}
