'use strict';
(() => {
  const hero = document.querySelector('.hero');
  if (!hero || !Array.isArray(products)) return;
  const money = n => new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(n);
  const valid = p => p && p.available !== false && p.name && safeUrl(p.imageUrl) && safeUrl(p.affiliateUrl);
  const recorded = p => valid(p) && Number.isFinite(p.price) && p.price > 0
    && p.priceCheck?.status === 'verified' && p.priceCheck.price === p.price
    && p.priceCheck.oldPrice === p.oldPrice && p.priceCheck.currency === 'BRL'
    && Number.isFinite(Date.parse(p.priceCheck.checkedAt));
  const fresh = products.filter(p => recorded(p) && MiraQuality.usablePrice(p));
  const bigDeals = fresh.filter(p => p.oldPrice > p.price && (1-p.price/p.oldPrice) >= .5)
    .sort((a,b)=>(1-b.price/b.oldPrice)-(1-a.price/a.oldPrice)).slice(0,8);
  const historical = products.filter(recorded);
  const slides = bigDeals.length ? bigDeals : fresh.length ? fresh.slice(0,8) : historical.slice(0,8);
  const shell = element('div','hero-static'), copy = element('div','hero-static-copy');
  copy.append(element('div','hero-static-eyebrow','PRODUTOS EM DESTAQUE'),
    element('h1','','Encontre uma boa oferta sem perder tempo.'),
    element('p','','Compare preços e explore produtos selecionados para comprar com mais clareza.'));
  const actions = element('div','hero-static-actions');
  const offers = element('a','hero-primary','Explorar ofertas →'); offers.href='#ofertas';
  const guides = element('a','hero-secondary','Ver guias e reviews'); guides.href='blog/';
  actions.append(offers,guides); copy.append(actions);
  copy.append(element('p','hero-static-note','Preços podem mudar. Confirme o valor e a disponibilidade na loja.'));
  const dashboard = element('div','hero-dashboard'), deal = element('article','hero-deal');
  const visual = element('div','hero-deal-visual'), info = element('div','hero-deal-info');
  const kicker = element('span','hero-card-kicker'), title = element('h2');
  const old = element('span','hero-old-price'), price = element('strong','hero-deal-price');
  const link = element('a','hero-deal-link');
  link.rel='sponsored nofollow noopener';
  const controls = element('div','hero-controls');
  const previous = element('button','','‹'), next = element('button','','›');
  previous.type=next.type='button';
  previous.setAttribute('aria-label','Oferta anterior');
  next.setAttribute('aria-label','Próxima oferta');
  const position = element('span','hero-position');
  controls.append(previous,position,next);
  info.append(kicker,title,old,price,link,controls); deal.append(visual,info); dashboard.append(deal);
  let index=0;
  function render() {
    const available = slides.filter(recorded);
    if (!available.length) {
      visual.replaceChildren(element('span','hero-empty-icon','↗'));
      kicker.textContent='EXPLORE O CATÁLOGO';
      title.textContent='Encontre sua próxima compra';
      old.textContent=price.textContent='';
      link.textContent='Ver produtos →'; link.href='#ofertas'; link.removeAttribute('target');
      controls.hidden=true; return;
    }
    index %= available.length;
    const p=available[index], img=element('img');
    img.src=p.imageUrl; img.alt=p.name; img.width=360; img.height=270; img.decoding='async';
    visual.classList.remove('image-error');
    img.addEventListener('error',()=>visual.classList.add('image-error'),{once:true});
    visual.replaceChildren(img);
    const current = MiraQuality.usablePrice(p);
    const discount=current && p.oldPrice>p.price ? Math.floor((1-p.price/p.oldPrice)*100) : 0;
    const date = new Date(p.priceCheck.checkedAt).toLocaleDateString('pt-BR',{timeZone:'America/Sao_Paulo'});
    kicker.textContent=current
      ? discount>=50 ? discount+'% OFF · PREÇO VERIFICADO' : 'PREÇO VERIFICADO'
      : 'ÚLTIMO PREÇO REGISTRADO EM '+date;
    title.textContent=p.name;
    old.textContent=discount>=50 ? 'De '+money(p.oldPrice) : '';
    price.textContent=money(p.price);
    link.textContent='Ver oferta na loja →'; link.href=p.affiliateUrl; link.target='_blank';
    position.textContent=(index+1)+' / '+available.length;
    controls.hidden=available.length<2;
  }
  const move=n=>{index=(index+n+slides.length)%slides.length;render();};
  previous.addEventListener('click',()=>move(-1)); next.addEventListener('click',()=>move(1));
  render();
  if(slides.length>1) setInterval(()=>{
    if(!document.hidden && !deal.matches(':hover') && !deal.contains(document.activeElement)
      && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) move(1);
  },5500);
  setInterval(render,60000);
  const side=element('div','hero-side'), guide=element('a','hero-info-card hero-guide-card');
  guide.href='blog/';
  guide.append(element('span','hero-card-kicker','GUIAS E REVIEWS'),
    element('h3','','Pesquise antes de comprar'),
    element('p','','Análises e comparações para ajudar na sua escolha.'),
    element('span','hero-card-link','Ver conteúdos →'));
  side.append(guide);
  const counts=products.filter(valid).reduce((acc,p)=>{
    if(p.category) acc[p.category]=(acc[p.category]||0)+1;
    return acc;
  },{});
  const categories=element('div','hero-info-card hero-category-card');
  categories.append(element('span','hero-card-kicker','EXPLORE RÁPIDO'),
    element('h3','','Vá direto ao que interessa'));
  const chips=element('div','hero-category-chips');
  Object.entries(counts).sort((a,b)=>b[1]-a[1]).slice(0,3).forEach(([name,count])=>{
    const button=element('button','hero-category-chip',name+' · '+count);
    button.type='button';
    button.addEventListener('click',()=>{
      [...document.querySelectorAll('.category')].find(item=>item.dataset.category===name)?.click();
      document.querySelector('#ofertas')?.scrollIntoView({behavior:'smooth',block:'start'});
    });
    chips.append(button);
  });
  categories.append(chips); side.append(categories); dashboard.append(side);
  shell.append(copy,dashboard); hero.replaceChildren(shell);
})();
