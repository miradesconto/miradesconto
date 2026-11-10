/* Testa o alternador real sem navegador ou dependências externas. */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('modo-visual.js', 'utf8');

function fixture(saved, search='') {
  const values = new Map();
  if (saved) values.set('miradesconto-modo-visual', saved);
  const callbacks = new Map();
  const attrs = new Map([['data-mira-layout', 'classic']]);
  const bodyClasses = new Set();
  const metaAttrs = new Map([['content', '#0f172a']]);
  const state = { urlChanged: false, replaceUrl: null, searchValue: 'notebook RTX' };
  const choices = ['classic', 'gamer'].map(name => {
    const attr = new Map([['data-layout-option', name]]);
    return {
      getAttribute(k) { return attr.get(k) || null; },
      setAttribute(k,v) { attr.set(k,String(v)); },
      removeAttribute(k) { attr.delete(k); },
      addEventListener(type,fn) { if (type==='click') callbacks.set(name,fn); }
    };
  });
  const pageUrl='https://miradesconto.com.br/'+(search || '');
  const location=new URL(pageUrl);
  const sandbox = {
    URL, URLSearchParams,
    window: {
      location,
      localStorage: {
        getItem(k){return values.get(k) || null;},
        setItem(k,v){values.set(k,v);}
      },
      history: {
        state: {page:'offers'},
        replaceState(_state,_title,url){state.replaceUrl=url;}
      }
    },
    document: {
      documentElement: {
        setAttribute(k,v){attrs.set(k,v);},
        getAttribute(k){return attrs.get(k) || null;}
      },
      body: {classList:{toggle(k,v){if(v)bodyClasses.add(k);else bodyClasses.delete(k);}}},
      querySelectorAll(q){assert.equal(q,'[data-layout-option]');return choices;},
      querySelector(q){
        return q==='meta[name="theme-color"]'
          ? {setAttribute(k,v){metaAttrs.set(k,v);}}
          : null;
      }
    }
  };
  vm.runInNewContext(source,sandbox,{filename:'modo-visual.js'});
  return {
    mode:()=>attrs.get('data-mira-layout'),
    saved:()=>values.get('miradesconto-modo-visual'),
    dark:()=>bodyClasses.has('mira-mode-dark'),
    meta:()=>metaAttrs.get('content'),
    replaceUrl:()=>state.replaceUrl,
    text:()=>state.searchValue,
    chosen:name=>choices.find(e=>e.getAttribute('data-layout-option')===name).getAttribute('aria-current'),
    click(name, options={}) {
      let prevented=false;
      callbacks.get(name)({
        button:0,metaKey:false,ctrlKey:false,shiftKey:false,altKey:false,
        defaultPrevented:false,
        preventDefault(){prevented=true;},
        ...options
      });
      return prevented;
    }
  };
}

// Visitantes novos: Clássico é padrão. A mudança é instantânea e não navega.
const visit=fixture(null);
assert.equal(visit.mode(),'classic');
assert.equal(visit.click('gamer'),true);
assert.equal(visit.mode(),'gamer');
assert.equal(visit.saved(),'gamer');
assert.equal(visit.dark(),true);
assert.equal(visit.meta(),'#080f1d');
assert.equal(visit.chosen('gamer'),'true');
assert.equal(visit.chosen('classic'),null);
assert.equal(visit.text(),'notebook RTX');
assert.equal(visit.click('classic'),true);
assert.equal(visit.mode(),'classic');
assert.equal(visit.saved(),'classic');
assert.equal(visit.dark(),false);
assert.equal(visit.meta(),'#0f172a');
assert.equal(visit.text(),'notebook RTX');

// Preferência persiste em nova visita.
assert.equal(fixture('gamer').mode(),'gamer');

// Link antigo /gamer.html redireciona para ?modo=gamer; mantém outros parâmetros.
const deep=fixture('classic','?modo=gamer&origem=radar#ofertas');
assert.equal(deep.mode(),'gamer');
assert.equal(deep.saved(),'gamer');
assert.equal(deep.replaceUrl(),'/?origem=radar#ofertas');

// Ctrl+click conserva comportamento nativo do navegador; JS não intercepta.
assert.equal(deep.click('classic',{ctrlKey:true}),false);
assert.equal(deep.mode(),'gamer');
console.log('OK: Clássico/Gamer alternam na mesma home, preservam estado e preferência.');
