'use strict';
const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict');
const text = fs.readFileSync('interface.js','utf8');
const events = [];
let responseText = '', calls = 0;
const context = {window:{MIRA_DATA:{products:[]},location:{search:''}}, URLSearchParams, URL,
  document:{hidden:false,dispatchEvent:e=>events.push(e.type)}, CustomEvent:class {constructor(type){this.type=type}},
  fetch:async()=>{calls++;return {ok:true,text:async()=>responseText}}};
vm.createContext(context);
vm.runInContext(text.slice(0,text.indexOf('function money')),context);
vm.runInContext('function renderProducts() {}',context);
vm.runInContext(text.slice(text.indexOf('let catalogRefreshing'),text.indexOf('\nrefreshCatalog();')),context);
(async()=>{
  const item={id:'MLB123',name:'Mouse',affiliateUrl:'https://meli.la/Test'};
  responseText='// generated\nwindow.MIRA_DATA = '+JSON.stringify({products:[item]})+';';
  await context.refreshCatalog();
  assert.equal(context.window.MIRA_DATA.products[0].id,item.id);
  assert.deepEqual(events,['mira:catalog-updated']);
  for(const bad of ['window.MIRA_DATA = {}; window.evil = true;', 'window.MIRA_DATA = {invalid};', 'window.MIRA_DATA = '+JSON.stringify({products:[item,item]})+';']){
    responseText=bad; await context.refreshCatalog();
    assert.equal(context.window.MIRA_DATA.products.length,1);
    assert.equal(events.length,1);
    assert.equal(context.window.evil,undefined);
  }
  context.document.hidden=true;
  const before=calls;await context.refreshCatalog();assert.equal(calls,before);
  console.log('OK: catálogo atualiza sem executar JS; falhas e duplicatas preservam dados; aba oculta não consulta.');
})().catch(e=>{console.error(e);process.exitCode=1});
