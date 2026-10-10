import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import fs from 'node:fs';

const code=fs.readFileSync(new URL('../../../historico.js',import.meta.url),'utf8');
const NOW=Date.parse('2026-10-10T00:30:00Z'),id='MLB4408547152';
class Clock extends Date {static now(){return NOW;}}
class Element {
  constructor(tag){this.tag=tag;this.children=[];this.attrs={};this.dataset={};this.listeners={};this.ownText='';}
  append(...items){for(const item of items){this.children.push(item);item.parent=this;}}
  replaceChildren(...items){this.children=[];this.ownText='';this.append(...items);}
  set textContent(text){this.ownText=text;this.children=[];}
  get textContent(){return this.ownText+this.children.map(child=>child.textContent).join(' ');}
  setAttribute(key,value){this.attrs[key]=String(value);}
  addEventListener(name,fn){(this.listeners[name]||=[]).push(fn);}
  querySelectorAll(tag){return this.children.flatMap(child=>[...(child.tag===tag?[child]:[]),...child.querySelectorAll(tag)]);}
  click(){for(const fn of this.listeners.click||[])fn();}
  showModal(){this.open=true;}
  close(){for(const fn of this.listeners.close||[])fn();}
  remove(){this.parent.children=this.parent.children.filter(child=>child!==this);}
}
function fixture(payload,status=200,base='https://worker.example') {
  const body=new Element('body'),calls=[];
  const document={body,createElement:tag=>new Element(tag),createElementNS:(_,tag)=>new Element(tag)};
  const window={MIRA_HISTORY_CONFIG:{apiBaseUrl:base}};
  const sandbox={window,document,URL,Date:Clock,AbortController,setTimeout,clearTimeout,
    MiraQuality:{usablePrice:()=>false},async fetch(url,init){calls.push({url:String(url),init});return {ok:status===200,status,json:async()=>payload};}};
  vm.runInNewContext(code,sandbox);
  return {window,body,calls,sandbox,product:{id,name:'Produto',price:110,oldPrice:150,priceCheck:{method:'poly-card-v1',variationId:'123'}}};
}
const row=extra=>({at:new Date(NOW-86400000).toISOString(),itemId:id,variationId:'123',method:'poly-card-v1',price:100,reference:150,...extra});
const payload=rows=>({schemaVersion:1,productId:id,currency:'BRL',observations:rows});

test('modal busca somente GET no Worker, sem token e sem arquivos JSON locais',async()=>{
  const h=fixture(payload([row({})]));await h.window.MiraHistory.open(h.product);
  assert.equal(h.calls[0].url,'https://worker.example/api/history/'+id);
  assert.equal(h.calls[0].init.credentials,'omit');assert.equal(h.calls[0].init.headers,undefined);
  assert.equal(h.body.querySelectorAll('circle').length,1);
});

test('gráfico exclui outro anúncio/variação, futuro, dados antigos e método desconhecido',async()=>{
  const good=[row({price:90}),row({at:new Date(NOW-3*86400000).toISOString(),price:100})];
  const bad=[row({itemId:'MLB9999999999',price:1}),row({variationId:'456',price:1}),
    row({at:new Date(NOW+86400000).toISOString(),price:1}),row({at:new Date(NOW-181*86400000).toISOString(),price:1}),
    row({method:'unknown',price:1}),row({price:true}),row({price:'1'})];
  const h=fixture(payload([...good,...bad]));await h.window.MiraHistory.open(h.product);
  assert.equal(h.body.querySelectorAll('circle').length,2);
  assert.match(h.body.textContent,/2 observações/);assert.match(h.body.textContent,/90,00/);
  assert.ok(!h.body.querySelectorAll('polyline')[0].attrs.points.includes('NaN'));
  h.body.querySelectorAll('button').find(button=>button.dataset.days===30).click();
  assert.equal(h.body.querySelectorAll('circle').length,2);
});

test('produto/moeda/schema divergente não cria gráfico',async()=>{
  for(const change of [{productId:'MLB9999999999'},{currency:'USD'},{schemaVersion:2}]){
    const h=fixture({...payload([row({})]),...change});await h.window.MiraHistory.open(h.product);
    assert.equal(h.body.querySelectorAll('svg').length,0);assert.match(h.body.textContent,/Não foi possível consultar/);
  }
});

test('configuração pendente ou insegura informa implantação sem buscar arquivo local',async()=>{
  for(const base of ['','http://external.example','https://user:pass@worker.example','https://worker.example/go']){
    const h=fixture({},200,base);await h.window.MiraHistory.open(h.product);
    assert.equal(h.calls.length,0);assert.match(h.body.textContent,/implantação/);
  }
});

test('404 mostra ausência de registros; 503 informa falha temporária',async()=>{
  const missing=fixture({},404);await missing.window.MiraHistory.open(missing.product);assert.match(missing.body.textContent,/Ainda não há histórico/);
  const down=fixture({},503);await down.window.MiraHistory.open(down.product);assert.match(down.body.textContent,/Não foi possível consultar/);
});

test('fechar o modal aborta a consulta e devolve foco ao botão',async()=>{
  const h=fixture(payload([]));let aborted=false,focus=0;
  h.sandbox.fetch=(_,init)=>new Promise((_,reject)=>init.signal.addEventListener('abort',()=>{aborted=true;reject(Error('aborted'));}));
  const opening=h.window.MiraHistory.open(h.product,{focus(){focus++;}});
  h.body.querySelectorAll('dialog')[0].close();await opening;
  assert.equal(aborted,true);assert.equal(focus,1);assert.equal(h.body.children.length,0);
});
