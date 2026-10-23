'use strict';
const assert=require('node:assert/strict');
const a=require('../afiliados.js');
for(const url of ['https://evil.test/?url=https://amzn.to/ABC','https://amazon.com.br.evil.test/dp/B012345678?tag=x','javascript:alert(1)','http://meli.la/abc','https://user@amzn.to/abc','https://amzn.to:8443/abc']) assert.equal(a.platform(url),null,url);
for(const [url,store] of [['https://meli.la/Test','mercadolivre'],['https://amzn.to/Test','amazon'],['https://www.amazon.com.br/dp/B012345678?tag=teste-20','amazon'],['https://s.shopee.com.br/Test','shopee']]) {
 assert.equal(a.platform(url),store);
 const p={affiliateUrl:url,affiliateVerified:true,affiliateLinkType:'product'};
 assert.equal(a.individual(p),true);
 assert.equal(a.individual({...p,available:false}),false);
 assert.equal(a.individual({...p,affiliateLinkType:'list'}),false);
 if(store!=='mercadolivre')assert.equal(a.individual({...p,affiliateVerified:false}),false);
}
assert.equal(a.platform('https://www.amazon.com.br/dp/B012345678'),null);
assert.equal(a.individual({affiliateUrl:'https://meli.la/1NguveN'}),false);
console.log('OK: três lojas, links confirmados, listas e domínios impostores bloqueados');
