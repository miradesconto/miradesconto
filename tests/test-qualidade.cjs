const assert = require('node:assert/strict');
const {usablePrice} = require('../qualidade.js');
const now = Date.parse('2026-09-20T20:00:00Z');
const p = {id:'MLB4592320910',price:49.99,oldPrice:135.41,available:null,
    priceCheck:{status:'verified',method:'poly-card-v1',itemId:'MLB4592320910',currency:'BRL',
    price:49.99,oldPrice:135.41,checkedAt:'2026-09-20T20:00:00Z'}};
assert.equal(usablePrice(p,now),true);
assert.equal(usablePrice(p,now+86400000),true);
assert.equal(usablePrice(p,now+86400001),false);
assert.equal(usablePrice(p,now-1),false);
for(const change of [{priceCheck:undefined},{price:1},{oldPrice:999},{available:false},{price:NaN}])
    assert.equal(usablePrice({...p,...change},now),false);
for(const checkedAt of ['2026-09-20T20:00:00','invalid',null])
    assert.equal(usablePrice({...p,priceCheck:{...p.priceCheck,checkedAt}},now),false);
console.log('OK: regras de preço verificado e expiração no navegador');
const api = {...p,itemId:'MLB9876543210',priceCheck:{...p.priceCheck,method:'ml-sale-price-v1',itemId:'MLB9876543210'}};
assert.equal(usablePrice(api,now),true);
assert.equal(usablePrice({...api,itemId:p.id},now),false);
assert.equal(usablePrice({...api,itemId:undefined},now),false);
assert.equal(usablePrice(api,now+86400001),false);
