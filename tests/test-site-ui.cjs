'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const {radarPriceIsRecent, refreshRadar} = require('../radar/radar.js');
const now = Date.parse('2026-10-13T20:00:00Z');
for (const [stamp, expected] of [
  ['2026-10-13T19:00:00Z', true], ['2026-10-13T18:00:00Z', true],
  ['2026-10-13T17:59:59Z', false], ['2026-10-13T21:00:00Z', false],
  ['2026-10-13T19:00:00', false], ['', false], [undefined, false],
]) assert.equal(radarPriceIsRecent(stamp, now), expected, String(stamp));
const nodes = Object.fromEntries(['.radar-badge','.radar-price','.radar-reason','.radar-primary'].map(s => [s,{textContent:'original',hidden:false}]));
const card = {dataset:{checkedAt:'2026-10-13T17:00:00Z'},querySelector:s => nodes[s]};
refreshRadar({querySelectorAll:()=>[card]}, now);
assert.equal(nodes['.radar-badge'].hidden,true);
assert.equal(nodes['.radar-price'].textContent,'Consultar preço na loja');
assert.match(nodes['.radar-reason'].textContent,/históricas/);
// Offline image failures must retain the source and surrounding purchase link.
function imageFixture({complete, naturalWidth, existingFallback}) {
  const events = {};
  const img = {complete,naturalWidth,hidden:false,src:'https://example.invalid/original.webp',
    parentElement:{querySelector:()=>existingFallback},
    addEventListener:(name, fn)=>events[name]=fn,
    setAttribute:(name,value)=>img[name]=value,removeAttribute:name=>delete img[name],
    after:node=>img.fallback=node};
  const doc = {querySelectorAll:()=>[img],getElementById:()=>null,createElement:()=>({})};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../blog/blog.js'),'utf8'),{document:doc});
  return {img,events,fallback:existingFallback||img.fallback};
}
for (const existingFallback of [undefined,{hidden:false}]) {
  const {img,events,fallback} = imageFixture({complete:false,naturalWidth:0,existingFallback});
  assert.equal(fallback.hidden,true,'loading is not a confirmed failure');
  events.error();assert.equal(img.hidden,true);assert.equal(fallback.hidden,false);
  assert.equal(img.src,'https://example.invalid/original.webp');
  events.load();assert.equal(img.hidden,false);assert.equal(fallback.hidden,true);
  assert.equal(img['aria-hidden'],undefined);
}
assert.equal(imageFixture({complete:true,naturalWidth:0}).fallback.hidden,false);
assert.equal(imageFixture({complete:true,naturalWidth:480}).fallback.hidden,true);
console.log('OK: image loading/error/recovery and Radar expiry boundaries');


// An existing product analysis takes precedence over an injected blog guide.
// Repeated connector passes must never produce more than one editorial CTA.
function editorialFixture(id, count) {
  const links=[];
  const buttons={};
  const body={
    querySelectorAll(selector) {
      assert.equal(selector,'a.product-link');
      return [...links];
    },
    querySelector(selector) {
      return selector==='.buttons' ? buttons : null;
    },
    insertBefore(link, target) {
      assert.equal(target,buttons);
      links.push(link);
    },
  };
  for(let i=0;i<count;i++) {
    const link={href:'/produtos/analise-'+i+'/'};
    link.remove=()=>{const at=links.indexOf(link);if(at!==-1)links.splice(at,1);};
    links.push(link);
  }
  return {dataset:{id},querySelector:s=>s==='.card-content'?body:null,links};
}
const editorialCards=[editorialFixture('MLB111',2),editorialFixture('MLB222',0)];
const editorialGrid={querySelectorAll:selector=>{
  assert.equal(selector,'.card[data-id]');
  return editorialCards;
}};
let runEditorial;
const editorialDocument={
  getElementById(id) {
    if(id==='productList')return editorialGrid;
    if(id==='editorial-data')return {textContent:JSON.stringify([{ids:['MLB111','MLB222'],title:'Guia revisado',url:'/blog/guia/' }])};
    return null;
  },
  createElement(tag){
    assert.equal(tag,'a');
    return {setAttribute(key,value){this[key]=value;}};
  },
};
class EditorialObserver {
  constructor(callback){runEditorial=callback;}
  observe(node,options){assert.equal(node,editorialGrid);assert.equal(options.childList,true);}
}
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../blog/conectar-ofertas.js'),'utf8'),{
  document:editorialDocument, MutationObserver:EditorialObserver,
});
assert.equal(editorialCards[0].links.length,1,'Análise original deve ter prioridade');
assert.equal(editorialCards[0].links[0].href,'/produtos/analise-0/');
assert.equal(editorialCards[1].links.length,1,'Um guia deve ser inserido quando não existir link');
assert.equal(editorialCards[1].links[0].href,'/blog/guia/');
runEditorial();
assert.equal(editorialCards[0].links.length,1,'Não duplicar links em chamadas posteriores');
assert.equal(editorialCards[1].links.length,1,'Não inserir guias duplicados');
const catalogCss=fs.readFileSync(path.join(__dirname,'../catalogo.css'),'utf8');
assert.match(catalogCss,/\.card \.card-content > a\.product-link:hover/);
assert.match(catalogCss,/text-decoration: none;/);
console.log('OK: apenas um link editorial por card e estilo secundário com hover');
