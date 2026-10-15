'use strict';
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync('interface.js', 'utf8');
const context = {window:{MIRA_DATA:{products:[]},location:{search:''}},URLSearchParams,document:{getElementById:id=>({value:id==='sortSelect'?'default':''})},MiraQuality:require('../qualidade.js')};
vm.createContext(context);
vm.runInContext(source.slice(0,source.indexOf('const categoryContainer')),context);
const ids = items => Array.from(items,p=>p.id);
const sample = Array.from({length:60},(_,i)=>({id:String(i).padStart(3,'0'),category:['Setup','Gaming','Celulares'][i%3]}));
const first = context.rotateOffers(sample,3600000);
const next = context.rotateOffers(sample,7200000);
assert.equal(first.length,60);
assert.equal(new Set(ids(first)).size,60);
assert.deepEqual(ids(first),ids(context.rotateOffers(sample,3601000)));
assert.notDeepEqual(ids(first.slice(0,24)),ids(next.slice(0,24)));
assert.equal(new Set(Array.from(first.slice(0,3),p=>p.category)).size,3);
assert.deepEqual(ids(context.rotateOffers([],3600000)),[]);
assert.deepEqual(ids(context.rotateOffers(sample.slice(0,1),3600000)),['000']);
const now = Date.now();
const fixture = (id,age,featured=false) => ({id,name:id,category:'Setup',featured,affiliateUrl:'https://meli.la/'+id.replace(/[^A-Za-z0-9]/g,''),price:100,oldPrice:null,priceCheck:{status:'verified',method:'poly-card-v1',currency:'BRL',itemId:id,price:100,oldPrice:null,checkedAt:new Date(now-age).toISOString()}});
context.fixtures=[fixture('fresh-featured',1000,true),fixture('fresh-other',1000),fixture('expired',25*3600000),{...fixture('unavailable',1000),available:false},{...fixture('unapproved',1000),affiliateUrl:'https://mercadolivre.com.br/normal'}];
vm.runInContext('products.push(...fixtures)',context);
assert.deepEqual(ids(context.filteredProducts()),['fresh-featured','fresh-other','expired']); // Valid offers first; expired last.
context.document.getElementById=id=>({value:id==='sortSelect'?'lowPrice':''});
vm.runInContext('products[1].price=50;products[1].priceCheck.price=50',context);
assert.deepEqual(ids(context.filteredProducts()),['fresh-other','fresh-featured','expired']);
// Sorting by highest price must also place a price pending review after verified products.
context.document.getElementById=id=>({value:id==='sortSelect'?'highPrice':''});
assert.deepEqual(ids(context.filteredProducts()),['fresh-featured','fresh-other','expired']);
// Even an old nominal discount must not outrank a valid offer.
context.fixtures[2].oldPrice=1000;
context.fixtures[2].priceCheck.oldPrice=1000;
context.document.getElementById=id=>({value:id==='sortSelect'?'discount':''});
assert.equal(ids(context.filteredProducts()).at(-1),'expired');
context.document.getElementById=id=>({value:id==='sortSelect'?'default':''});
vm.runInContext("selectedCategory='Destaques'",context);
assert.deepEqual(ids(context.filteredProducts()),['fresh-featured']);
console.log('OK: ofertas com preço validado aparecem antes das sem preço nos filtros e ordenações, mantendo o rodízio e a exclusão de links não individuais.');
