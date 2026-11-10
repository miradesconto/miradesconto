/* Hero contract: verified catalog may be empty, but Shopee snapshot still renders real product. */
'use strict';
const fs=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');

const js=fs.readFileSync('carrossel.js','utf8');
const html=fs.readFileSync('index.html','utf8');
const snapshot=JSON.parse(fs.readFileSync('_data/ofertas_automaticas.json','utf8'));
assert.match(html,/id="hero-product-seeds"/);
assert.match(html,/data-hero-offer/);
assert.match(html,/site\.data\.ofertas_automaticas/);
assert.ok(snapshot.some(x=>x.loja==='Shopee'&&/^\/assets\/ofertas\/[a-f0-9]{24}\.(?:jpg|png|webp)$/.test(x.imagem)));

class Elem {
  constructor(tag='div',cls='',text) {
    this.tag=tag; this.className=cls;this.children=[];this.textContent=text??'';
    this.dataset={};this.events={};this.attrs={};this.hidden=false;
    this.classList={add(){},remove(){}};
  }
  append(...children){this.children.push(...children);}
  replaceChildren(...children){this.children=children;}
  querySelector(selector){
    const target=selector.toLowerCase();
    return this.walk().find(x=>
      (target==='a'&&x.tag==='a') ||
      (target==='.hero-feature-visual img'&&x.tag==='img') ||
      (target==='.hero-feature-details h2'&&x.tag==='h2') ||
      (target==='.hero-price'&&x.className==='hero-price') ||
      (target==='.hero-offer-link'&&x.className==='hero-offer-link')
    )||null;
  }
  walk(){
    const out=[];
    for(const child of this.children)if(child instanceof Elem){out.push(child,...child.walk());}
    return out;
  }
  get lastChild(){return this.children[this.children.length-1]||null;}
  setAttribute(k,v){this.attrs[k]=v;}
  removeAttribute(k){delete this.attrs[k];}
  addEventListener(k,fn){this.events[k]=fn;}
  matches(){return false;}
  contains(){return false;}
}
const hero=new Elem('section','hero');
const nodes=snapshot.slice(0,35).map(x=>({
  dataset:{title:x.titulo,image:x.imagem,affiliate:x.link_afiliado,store:x.loja,price:String(x.preco_atual)}
}));
const fakeDocument={
  hidden:false,
  activeElement:null,
  querySelector(q){
    if(q==='.hero')return hero;
    return null;
  },
  querySelectorAll(q){
    assert.equal(q,'#hero-product-seeds [data-hero-offer]');
    return nodes;
  },
  createElement(tag){return new Elem(tag);},
  addEventListener(){}
};
const window={
  MiraHomepageSelection:[],
  matchMedia(){return {matches:false};}
};
const MiraQuality={
  priceReviewReason(){return 'stale';},
  usablePrice(){return false;}
};
const sandbox={
  document:fakeDocument,window,products:[],
  MiraQuality,
  safeUrl(){return false;},
  directAffiliate(){return false;},
  rotateOffers(x){return x;},
  isAffiliateList(){return false;},
  element(tag,cls,text){return new Elem(tag,cls,text);},
  sessionStorage:{getItem(){return null;},setItem(){}},
  setInterval(){},
  URL,Number,Math,Intl,Date,Array,Set,Map,String
};
vm.runInNewContext(js,sandbox,{filename:'carrossel.js'});
const headline=hero.querySelector('.hero-feature-details h2');
const image=hero.querySelector('.hero-feature-visual img');
const price=hero.querySelector('.hero-price');
const link=hero.querySelector('.hero-offer-link');
assert.ok(headline&&image&&price&&link,'Hero deve conter título, foto, preço e CTA');
assert.match(headline.textContent,/Monitor/i,'O primeiro destaque deve ser monitor real');
assert.match(image.src,/^\/assets\/ofertas\/[a-f0-9]{24}\.(?:jpg|png|webp)$/);
assert.match(link.href,/^https:\/\/s\.shopee\.com\.br\//);
assert.match(price.textContent,/A partir de R\$/);
assert.notEqual(headline.textContent,'Encontre sua próxima compra');
assert.equal(link.target,'_blank');
assert.match(link.rel,/sponsored/);

const next=hero.walk().find(x=>x.tag==='button'&&x.attrs['aria-label']==='Próxima oferta');
assert.ok(next&&next.events.click,'carrossel deve continuar navegável');
next.events.click();
const nextImage=hero.querySelector('.hero-feature-visual img');
assert.ok(nextImage&&/^\/assets\/ofertas\//.test(nextImage.src));
console.log('OK: hero mostra foto local + produto Shopee quando catálogo de preços verificados está vazio.');
