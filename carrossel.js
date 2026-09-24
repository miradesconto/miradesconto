'use strict';
(() => {
  const hero = document.querySelector('.hero');
  if (!hero || !Array.isArray(products)) return;
  const money = n => new Intl.NumberFormat('pt-BR', {style:'currency', currency:'BRL'}).format(n);
  const valid = p => p && p.available !== false && p.name && safeUrl(p.imageUrl) && safeUrl(p.affiliateUrl);
  const recorded = p => valid(p) && Number.isFinite(p.price) && p.price > 0
    && p.priceCheck?.status === 'verified' && p.priceCheck.price === p.price
    && p.priceCheck.oldPrice === p.oldPrice && p.priceCheck.currency === 'BRL'
    && Number.isFinite(Date.parse(p.priceCheck.checkedAt));
  const fresh = products.filter(p => recorded(p) && MiraQuality.usablePrice(p));
  const deals = fresh.filter(p => p.oldPrice > p.price && (1 - p.price / p.oldPrice) >= .5)
    .sort((a,b) => (1 - b.price / b.oldPrice) - (1 - a.price / a.oldPrice)).slice(0,8);
  const slides = deals.length ? deals : fresh.length ? fresh.slice(0,8) : products.filter(recorded).slice(0,8);
  const shell = element('div','hero-stage');
  const copy = element('div','hero-copy');
  const eyebrow = element('div','hero-eyebrow');
  eyebrow.append(element('span','hero-live-dot'), element('span','','RADAR MIRADESCONTO'));
  const heading = element('h1');
  heading.append('Boas compras começam com ', element('span','','preço na mira.'));
  copy.append(eyebrow, heading,
    element('p','hero-lede','Ofertas com foto, preço registrado e data de verificação. Encontre o que interessa e confira as condições antes de comprar.'));
  const actions = element('div','hero-actions');
  const explore = element('a','hero-primary','Explorar ofertas ↗'); explore.href='#ofertas';
  const guide = element('a','hero-secondary','Como escolhemos →'); guide.href='sobre.html';
  actions.append(explore, guide); copy.append(actions);
  const proof = element('div','hero-proof');
  const count = element('div','hero-proof-item');
  count.append(element('strong','',String(fresh.length)), element('span','','preços verificados nas últimas 24h'));
  const rhythm = element('div','hero-proof-item');
  rhythm.append(element('strong','','1 hora'), element('span','','entre as buscas automáticas'));
  proof.append(count,rhythm); copy.append(proof);
  const disclosure = element('p','hero-disclosure');
  disclosure.append('Links de afiliado. Podemos receber comissão, sem custo adicional. ',
    element('a','','Entenda a transparência ↗'));
  disclosure.querySelector('a').href='transparencia.html'; copy.append(disclosure);

  const showcase = element('div','hero-showcase');
  const top = element('div','hero-showcase-top');
  top.append(element('span','hero-showcase-label','OFERTA EM DESTAQUE'), element('span','hero-showcase-date'));
  const card = element('article','hero-feature');
  const visual = element('div','hero-feature-visual');
  const badge = element('span','hero-feature-badge');
  visual.append(badge);
  const details = element('div','hero-feature-details');
  const category = element('span','hero-feature-category');
  const title = element('h2');
  const values = element('div','hero-values');
  const old = element('span','hero-old-price');
  const price = element('strong','hero-price');
  values.append(old,price);
  const link = element('a','hero-offer-link','Ver produto na loja ↗');
  link.rel='sponsored nofollow noopener noreferrer'; link.target='_blank';
  details.append(category,title,values,link);
  card.append(visual,details);
  const footer = element('div','hero-showcase-footer');
  const status = element('span','hero-status');
  const controls = element('div','hero-controls');
  const previous = element('button','','‹'), position = element('span','hero-position'), next = element('button','','›');
  previous.type=next.type='button';
  previous.setAttribute('aria-label','Oferta anterior'); next.setAttribute('aria-label','Próxima oferta');
  controls.append(previous,position,next); footer.append(status,controls);
  const rail = element('div','hero-rail');
  showcase.append(top,card,footer,rail); shell.append(copy,showcase); hero.replaceChildren(shell);

  let index=0;
  function render() {
    if (!slides.length) {
      visual.replaceChildren(element('span','hero-empty-icon','↗'));
      badge.hidden=true; category.textContent='EXPLORE O CATÁLOGO';
      title.textContent='Encontre sua próxima compra';
      old.textContent=price.textContent=status.textContent='';
      link.textContent='Explorar produtos ↗'; link.href='#ofertas'; link.removeAttribute('target');
      controls.hidden=true; rail.hidden=true; top.lastChild.textContent=''; return;
    }
    index=(index+slides.length)%slides.length;
    const p=slides[index], current=MiraQuality.usablePrice(p);
    const discount=current && p.oldPrice>p.price ? Math.floor((1-p.price/p.oldPrice)*100) : 0;
    const date=new Date(p.priceCheck.checkedAt).toLocaleDateString('pt-BR',{timeZone:'America/Sao_Paulo'});
    const image=element('img'); image.src=p.imageUrl; image.alt=p.name;
    image.width=560; image.height=420; image.decoding='async';
    image.addEventListener('error',()=>visual.classList.add('image-error'),{once:true});
    visual.classList.remove('image-error'); visual.replaceChildren(image,badge);
    badge.hidden=discount<50; badge.textContent=discount+'% OFF';
    category.textContent=p.category || 'Mercado Livre'; title.textContent=p.name;
    old.textContent=current && discount>=50 ? 'De '+money(p.oldPrice) : '';
    price.textContent=money(p.price);
    link.textContent='Ver produto na loja ↗'; link.href=p.affiliateUrl; link.target='_blank';
    status.textContent=current ? 'Preço verificado em '+date : 'Último preço registrado em '+date;
    top.lastChild.textContent=current ? 'VERIFICADO RECENTEMENTE' : 'CONFIRME NA LOJA';
    position.textContent=(index+1)+' / '+slides.length;
    controls.hidden=slides.length<2;
    rail.hidden=slides.length<2;
    if (slides.length>1) {
      const previews=[];
      for (let offset=1; offset<=Math.min(3,slides.length-1); offset++) {
        const item=slides[(index+offset)%slides.length];
        const button=element('button','hero-rail-item'); button.type='button';
        button.setAttribute('aria-label','Mostrar oferta: '+item.name);
        const thumb=element('img'); thumb.src=item.imageUrl; thumb.alt=''; thumb.loading='lazy';
        thumb.addEventListener('error',()=>thumb.replaceWith(element('span','hero-rail-placeholder','↗')),{once:true});
        const label=element('span'); label.append(element('small','',item.category || 'Oferta'),element('strong','',money(item.price)));
        button.append(thumb,label); button.addEventListener('click',()=>{index=(index+offset)%slides.length;render();});
        previews.push(button);
      }
      rail.replaceChildren(...previews);
    }
  }
  previous.addEventListener('click',()=>{index--;render();});
  next.addEventListener('click',()=>{index++;render();});
  render();
  if (slides.length>1) setInterval(()=>{
    if (!document.hidden && !showcase.matches(':hover') && !showcase.contains(document.activeElement)
      && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {index++;render();}
  },6500);
  setInterval(render,60000);
})();
