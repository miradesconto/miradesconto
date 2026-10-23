'use strict';
/* Dedicated full catalogue. Never infer affiliate ownership from a generic list link. */
(() => {
  const PAGE_SIZE = 12;
  const GENERIC_LISTS = new Set(['https://meli.la/1NguveN', 'https://meli.la/1pyBZm8']);
  const byId = items => [...new Map(items.filter(p => p && typeof p.id === 'string' && p.name)
    .map(p => [p.id, p])).values()];
  const clean = value => String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  const countLinks = products => {
    const map = new Map();
    for (const p of products) {
      const url = p.affiliateUrl;
      if (typeof url === 'string') map.set(url, (map.get(url) || 0) + 1);
    }
    return map;
  };
  function individualLink(p, links, sources) {
    const url = p?.affiliateUrl;
    return p?.available !== false
      && typeof url === 'string'
      && (typeof window !== 'undefined' && window.MiraAffiliate ? window.MiraAffiliate.individual(p) : /^https:\/\/meli\.la\/[a-zA-Z0-9]+$/.test(url))
      && !GENERIC_LISTS.has(url)
      && !sources.includes(url)
      && p.affiliateLinkType !== 'list'
      && links.get(url) === 1 ? url : null;
  }
  const discount = p => Number.isFinite(p.oldPrice) && p.oldPrice > p.price && p.price > 0
    ? (p.oldPrice - p.price) / p.oldPrice : 0;
  function selectProducts(products, opts, quality, now = Date.now(), sources = []) {
    const unique = byId(products);
    const counts = countLinks(unique);
    const filtered = unique.filter(p =>
      (!opts.category || (p.category || 'Outros') === opts.category)
      && (!opts.search || clean([p.id, p.name, p.category, p.store].join(' ')).includes(clean(opts.search))));
    return filtered.sort((a,b) => {
      const aFresh = quality(a, now) === true, bFresh = quality(b, now) === true;
      if (aFresh !== bFresh) return aFresh ? -1 : 1;
      const aLink = !!individualLink(a, counts, sources), bLink = !!individualLink(b, counts, sources);
      if (aLink !== bLink) return aLink ? -1 : 1;
      if (aFresh) {
        if (opts.sort === 'low' && a.price !== b.price) return a.price - b.price;
        if (opts.sort === 'high' && a.price !== b.price) return b.price - a.price;
        if (opts.sort === 'discount' && discount(a) !== discount(b)) return discount(b) - discount(a);
      }
      if (opts.sort === 'name') return String(a.name).localeCompare(String(b.name), 'pt-BR');
      return Number(b.featured === true) - Number(a.featured === true)
        || String(a.name).localeCompare(String(b.name), 'pt-BR');
    });
  }

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { selectProducts, individualLink, countLinks, PAGE_SIZE };
  }
  if (typeof document === 'undefined' || typeof window === 'undefined') return;

  const grid = document.getElementById('catalogGrid');
  if (!grid) return;
  const $ = id => document.getElementById(id);
  const search = $('catalogSearch'), category = $('catalogCategory'), sort = $('catalogSort');
  const priceValid = (p, now) => window.MiraQuality?.usablePrice(p, now) === true;
  const money = n => new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(n);
  let rows = byId(window.MIRA_DATA?.products || []), sources = window.MIRA_DATA?.affiliateSources || [];
  let page = 1;
  const elem = (tag, cls, text) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const validImage = url => {
    try {
      const u = new URL(url);
      return u.protocol === 'https:' && !u.username && !u.password;
    } catch { return false; }
  };
  function makeCard(p, counts, now) {
    const fresh = priceValid(p, now);
    const card = elem('article','card');
    const visual = elem('div','picture');
    const fallback = elem('span','missing','Imagem indisponível');
    if (validImage(p.imageUrl)) {
      const img = elem('img');
      img.alt = p.name; img.loading = 'lazy'; img.decoding = 'async';
      img.width = 400; img.height = 300;
      img.addEventListener('error', () => {img.hidden=true;fallback.hidden=false;});
      img.addEventListener('load', () => {fallback.hidden=true;});
      fallback.hidden=true;img.src=p.imageUrl;visual.append(img);
    }
    visual.append(fallback);
    if (fresh && discount(p) >= 0.15) {
      const badge = elem('span','badge','-'+Math.round(discount(p)*100)+'%');
      badge.title = 'Comparação com a referência da loja, não com um histórico de preços.';
      visual.append(badge);
    }
    const body = elem('div','body');
    body.append(elem('p','category',p.category||'Tecnologia'),elem('h3','',p.name));
    const old=elem('p','old',fresh && discount(p)>0 ? money(p.oldPrice) : '');
    const price=elem('p','price'+(fresh?'':' missing-price'),fresh ? money(p.price) : 'Consultar preço na loja');
    const checked=elem('p','checked',fresh
      ? 'Conferido em '+new Date(p.priceCheck.checkedAt).toLocaleString('pt-BR',{timeZone:'America/Sao_Paulo'})+' (Brasília)'
      : 'Preço atual não confirmado nas últimas 2 horas');
    body.append(old,price,checked);
    const actions=elem('div','action-area');
    const link=individualLink(p,counts,sources);
    if (link) {
      const a=elem('a','shop','CONFERIR PREÇO NA LOJA');
      a.href=link; a.target='_blank';a.rel='sponsored nofollow noopener noreferrer';
      a.dataset.itemId=p.id; a.dataset.itemName=p.name;a.dataset.itemCategory=p.category||'';
      a.dataset.destinationType='product';a.dataset.linkLocation='full-catalog';
      actions.append(a);
      if (!window.MiraQuality?.priceReviewReason(p)) {
        const details=elem('a','shop','Detalhes e cuidados →');
        details.href='/oferta/'+p.id.toLowerCase()+'/';actions.append(details);
      }
      actions.append(elem('small','disclose','Link individual de afiliado'));
    } else {
      actions.append(elem('span','unlinked',p.available===false ? 'Produto indisponível' : 'Link individual de afiliado pendente'));
    }
    body.append(actions);card.append(visual,body);
    return card;
  }
  function setupCategories() {
    const selected = category.value;
    const all = [...new Set(rows.map(p=>p.category || 'Outros'))].sort((a,b)=>a.localeCompare(b,'pt-BR'));
    const allOption=elem('option','','Todas as categorias');
    allOption.value='';
    category.replaceChildren(allOption);
    for (const value of all) {
      const option=elem('option','',value);option.value=value;category.append(option);
    }
    category.value = all.includes(selected) ? selected : '';
  }
  function render() {
    const now=Date.now();
    const opts={search:search.value.trim(),category:category.value,sort:sort.value};
    const filtered=selectProducts(rows,opts,priceValid,now,sources);
    const pages=Math.max(1,Math.ceil(filtered.length/PAGE_SIZE));
    page=Math.min(page,pages);
    const onPage=filtered.slice((page-1)*PAGE_SIZE,page*PAGE_SIZE);
    const counts=countLinks(rows);
    grid.replaceChildren(...onPage.map(p=>makeCard(p,counts,now)));
    $('catalogEmpty').hidden=filtered.length!==0;
    const freshCount=filtered.filter(p=>priceValid(p,now)).length;
    $('catalogSummary').textContent=filtered.length+' produtos encontrados · '+freshCount+' com preço recente · '+(filtered.length-freshCount)+' para consultar na loja';
    $('catalogPage').textContent=filtered.length ? 'Página '+page+' de '+pages : '';
    $('catalogPrev').disabled=page===1 || !filtered.length;
    $('catalogNext').disabled=page===pages || !filtered.length;
  }
  for (const control of [search,category,sort]) control.addEventListener(control===search?'input':'change',()=>{page=1;render();});
  $('catalogPrev').addEventListener('click',()=>{if(page>1){page--;render();}});
  $('catalogNext').addEventListener('click',()=>{page++;render();});
  setupCategories();render();
  let busy=false;
  async function refresh() {
    if (busy || document.hidden) return;
    busy=true;
    try {
      const response=await fetch('/produtos.js',{cache:'no-store'});
      if (!response.ok) return;
      const script=await response.text();
      const match=script.match(/(?:^|\n)window\.MIRA_DATA\s*=\s*(\{[\s\S]*\})\s*;?\s*$/);
      if (!match) return;
      const next=JSON.parse(match[1]);
      if (!Array.isArray(next.products) || !next.products.length || next.products.some(p=>!p||!p.id||!p.name)) return;
      if (new Set(next.products.map(p=>p.id)).size!==next.products.length) return;
      rows=byId(window.MiraAffiliate ? window.MiraAffiliate.merge(next.products) : next.products);sources=Array.isArray(next.affiliateSources)?next.affiliateSources:[];
      setupCategories();render();
    } catch { /* Keep last valid catalogue; expiring prices are always hidden. */ }
    finally {busy=false;}
  }
  refresh();setInterval(refresh,5*60*1000);
  setInterval(render,60*1000);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh();});
})();
