'use strict';
const assert = require('node:assert/strict');
const radar = require('../radar.js');
const hour = 3600000, now = Date.parse('2026-10-13T01:00:00Z');
const item = (id, category) => ({id,category,checkedAt:new Date(now - 1000).toISOString(),actionable:true,strength:3,observations:10,spanDays:8,label:'Excelente preço',currentPrice:100,averagePrice:110,minimumPrice:95,affiliateUrl:'https://meli.la/Ab123',imageUrl:'https://example.com/image.jpg',deltaAveragePct:-9});
const items = Array.from({length:24}, (_,i) => item(String(i).padStart(3,'0'),['Setup','Gaming','Celulares','Áudio'][i % 4]));
const ids = list => list.map(p => p.id);
const first = radar.choose(items,now), next = radar.choose(items,now + hour);
assert.equal(first.length,12);
assert.equal(new Set(ids(first)).size,12);
assert.deepEqual(ids(first),ids(radar.choose(items,now + 1000)));
assert.notDeepEqual(ids(first),ids(next));
for (const category of ['Setup','Gaming','Celulares','Áudio']) assert.equal(first.filter(p => p.category === category).length,3);
assert.equal(radar.choose(items,now,'Setup').length,6);
assert.deepEqual(radar.choose(items,now + 3 * hour),[]);
for (const changes of [{actionable:false},{observations:5},{spanDays:6.9},{strength:1},{currentPrice:NaN},{label:'Preço estável'},{affiliateUrl:'https://example.com'},{checkedAt:'2026-10-13T01:01:00Z'},{checkedAt:'2026-10-13T00:00:00'}]) {
  assert.equal(radar.eligible({...items[0],...changes},now),false);
}
assert.equal(radar.fresh({...items[0],checkedAt:new Date(now - 2 * hour).toISOString()},now),true);
assert.equal(radar.fresh({...items[0],checkedAt:new Date(now - 2 * hour - 1).toISOString()},now),false);
console.log('OK: Radar varia os destaques, distribui categorias e exclui preço vencido, futuro ou sem evidência.');
