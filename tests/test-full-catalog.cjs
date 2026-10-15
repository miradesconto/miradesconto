'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const quality = require('../qualidade.js');
const {selectProducts,individualLink,countLinks,PAGE_SIZE}=require('../catalogo/vitrine-completa.js');
const now=Date.parse('2026-10-15T03:00:00Z');
const fresh=(id,price,extra={})=>({id,name:id,category:'Setup',store:'Mercado Livre',affiliateUrl:'https://meli.la/'+id,
  imageUrl:'https://http2.mlstatic.com/example.webp',price,oldPrice:price*1.5,available:true,
  priceCheck:{status:'verified',method:'poly-card-v1',currency:'BRL',itemId:id,price,oldPrice:price*1.5,
    checkedAt:new Date(now-1000).toISOString()},...extra});
const p1=fresh('MLB11111111',90);
const p2=fresh('MLB22222222',160);
const old=fresh('MLB33333333',30,{priceCheck:{...fresh('MLB33333333',30).priceCheck,checkedAt:new Date(now-7200001).toISOString()}});
const generic=fresh('MLB44444444',120,{affiliateUrl:'https://meli.la/1NguveN'});
const generic2=fresh('MLB55555555',140,{affiliateUrl:'https://meli.la/1NguveN'});
const rows=[old,p2,generic,p1,generic2];
const check=(p,t)=>quality.usablePrice(p,t);
const search=sort=>selectProducts(rows,{search:'',category:'',sort},check,now,['https://meli.la/1pyBZm8']);
for (const mode of ['featured','low','high','discount','name']) {
 const results=search(mode);
 assert.equal(results.length,5,'Preserve all catalogue records');
 assert.deepEqual(results.map(p=>check(p,now)),[true,true,true,true,false],'Price-unknown cards must be last: '+mode);
 assert.equal(results.at(-1).id,old.id);
}
assert.deepEqual(search('low').slice(0,2).map(p=>p.id),[p1.id,p2.id]);
assert.deepEqual(search('high').slice(0,2).map(p=>p.id),[p2.id,p1.id]);
assert.equal(selectProducts(rows,{search:'MLB333',category:'',sort:'featured'},check,now).length,1);
assert.equal(selectProducts(rows,{search:'',category:'Acessórios',sort:'featured'},check,now).length,0);
const counts=countLinks(rows);
assert.equal(individualLink(p1,counts,[]),p1.affiliateUrl);
assert.equal(individualLink(generic,counts,[]),null);
assert.equal(individualLink(generic2,counts,[]),null);
assert.equal(individualLink({...p1,available:false},counts,[]),null);
assert.equal(individualLink({...p1,affiliateUrl:'https://mercadolivre.com.br/produto'},counts,[]),null);
assert.equal(individualLink({...p1,affiliateUrl:'https://meli.la/1pyBZm8'},counts,['https://meli.la/1pyBZm8']),null);
assert.equal(PAGE_SIZE,12);
const html=fs.readFileSync('catalogo/index.html','utf8');
const home=fs.readFileSync('index.html','utf8');
const sitemap=fs.readFileSync('sitemap.xml','utf8');
assert.match(html,/Todos os produtos/);
assert.match(html,/catalogGrid/);
assert.match(home,/href="catalogo\/"/);
assert.match(sitemap,/https:\/\/miradesconto\.com\.br\/catalogo\//);
console.log('OK: catálogo completo, preço verificado primeiro, links individuais e navegação.');
