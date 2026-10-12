const assert = require('node:assert/strict');
const {usablePrice, priceReviewReason} = require('../qualidade.js');
const now = Date.parse('2026-09-20T20:00:00Z');
const p = {id:'MLB4592320910',price:49.99,oldPrice:135.41,available:null,
    priceCheck:{status:'verified',method:'poly-card-v1',itemId:'MLB4592320910',currency:'BRL',
    price:49.99,oldPrice:135.41,checkedAt:'2026-09-20T20:00:00Z'}};
assert.equal(usablePrice(p,now),true);
assert.equal(usablePrice(p,now+7200000),true);
assert.equal(usablePrice(p,now+7200001),false);
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
assert.equal(usablePrice(api,now+7200001),false);

// API verification does not guarantee a commercially plausible price.
const suspicious = {...p, id:'MLB6971944604', name:'Smart Tv 43 Full Hd P43cra Roku Tv Hdr10 Dolby Philco', price:9989, oldPrice:9999};
suspicious.priceCheck = {...p.priceCheck, itemId:suspicious.id, price:9989, oldPrice:9999};
assert.equal(priceReviewReason(suspicious), 'tv_43_fhd_above_review_limit');
assert.equal(usablePrice(suspicious, now), false);
const normalTv = {...suspicious, price:1699, oldPrice:1999,
    priceCheck:{...suspicious.priceCheck, price:1699, oldPrice:1999}};
assert.equal(priceReviewReason(normalTv), null);
assert.equal(usablePrice(normalTv, now), true);
assert.equal(priceReviewReason({...suspicious, name:'Notebook gamer Ryzen AI 9'}), null);
assert.equal(priceReviewReason({...suspicious, name:'Smart TV 43 4K OLED'}), null);
