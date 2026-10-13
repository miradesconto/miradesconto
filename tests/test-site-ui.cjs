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
