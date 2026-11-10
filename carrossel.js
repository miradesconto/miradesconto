'use strict';
(() => {
  const hero = document.querySelector('.hero');
  if (!hero || !Array.isArray(products)) return;
  const money = n => new Intl.NumberFormat('pt-BR', {style:'currency', currency:'BRL'}).format(n);
  const valid = p => p && p.available !== false && p.name && safeUrl(p.imageUrl) && safeUrl(p.affiliateUrl);
  const recorded = p => valid(p) && !MiraQuality.priceReviewReason(p) && Number.isFinite(p.price) && p.price > 0
    && p.priceCheck?.status === 'verified' && p.priceCheck.price === p.price
    && p.priceCheck.oldPrice === p.oldPrice && p.priceCheck.currency === 'BRL'
    && Number.isFinite(Date.parse(p.priceCheck.checkedAt));
  const fresh = products.filter(p => recorded(p) && MiraQuality.usablePrice(p) && directAffiliate(p));
  // Include the full eligible catalog, interleave categories, vary the starting point.
  const eligibleProducts = () => {
    const selection = window.MiraHomepageSelection || [];
    return [...new Map(products.filter(p => selection.includes(p.id) && valid(p) && MiraQuality.usablePrice(p)).map(p => [p.id, p])).values()];
  };
  /*
   * Reserva REAL da Shopee: o catálogo principal só exibe preços verificados e
   * pode ficar sem elegíveis após 2h. O feed de afiliados mantém ofertas com
   * fotos já espelhadas em /assets/ofertas/ pelo nosso próprio site.
   *
   * Os dados chegam escapados pelo Liquid; nunca usamos innerHTML.
   * Mesmo que a API da Shopee falhe temporariamente, o último snapshot
   * publicado permanece até a próxima atualização.
   */
  const offerNodes = [...document.querySelectorAll('#hero-product-seeds [data-hero-offer]')];
  const sourceRank = name => {
    const n = String(name).toLowerCase();
    let score = /monitor gamer/.test(n) ? 100 : /monitor/.test(n) ? 75 : 0;
    if (/odyssey|samsung/.test(n)) score += 35;
    if (/180hz|165hz|qhd/.test(n)) score += 12;
    if (/notebook/.test(n)) score += 90;
    if (/fone|headset|mouse|teclado/.test(n)) score += 50;
    if (/gt 210|miniatura|homem aranha|cabo hdmi|suporte para monitor|base para monitor/.test(n)) score -= 160;
    return score;
  };
  const feedOffers = offerNodes.map((node, i) => {
    const d = node.dataset;
    const name = (d.title || '').trim();
    const imageUrl = d.image || '';
    const affiliateUrl = d.affiliate || '';
    const loja = d.store || '';
    const price = Number(d.price);
    const localPhoto = /^\/assets\/ofertas\/[a-f0-9]{24}\.(?:jpg|webp|png)$/.test(imageUrl);
    let validLink = false;
    try {
      const uri = new URL(affiliateUrl);
      validLink = uri.protocol === 'https:'
        && ((loja === 'Shopee' && uri.hostname === 's.shopee.com.br')
        || (loja === 'Mercado Livre' && (uri.hostname === 'meli.la'
          || (uri.hostname.endsWith('mercadolivre.com.br') && uri.searchParams.has('matt_tool_id')))));
    } catch {}
    if (!name || !localPhoto || !validLink || !Number.isFinite(price) || price <= 0) return null;
    return {
      id: 'hero-feed-' + i, name, imageUrl, affiliateUrl,
      price, loja, category: loja === 'Shopee' ? 'Shopee • Tecnologia' : 'Mercado Livre • Tecnologia',
      isFeed: true, rank: sourceRank(name)
    };
  }).filter(Boolean);
  const best = (source, count) => source.sort((a, b) => b.rank - a.rank).slice(0, count);
  const shop = best(feedOffers.filter(p => p.loja === 'Shopee'), 6);
  const ml = best(feedOffers.filter(p => p.loja === 'Mercado Livre'), 3);
  const fallbackSlides = [
    ...shop.slice(0, 4), ...ml.slice(0, 2), ...shop.slice(4, 6), ...ml.slice(2, 3)
  ];
  const chooseSlides = () => {
    const featured = rotateOffers(eligibleProducts());
    if (!fallbackSlides.length) return featured;
    // Inicialmente mostramos ofertas Shopee reais. A navegação continua a
    // alternar também para itens já verificados do catálogo tradicional.
    return [...fallbackSlides, ...featured.filter(p =>
      !fallbackSlides.some(x => x.affiliateUrl === p.affiliateUrl))].slice(0, 15);
  };
  let slides = chooseSlides();
  let start = fallbackSlides.length ? 0 : Math.floor(Math.random() * Math.max(1, slides.length));
  try {
    const previousId = sessionStorage.getItem('mira:lastShowcase');
    if (slides.length > 1 && slides[start]?.id === previousId) start = (start + 1) % slides.length;
    if (slides[start]) sessionStorage.setItem('mira:lastShowcase', slides[start].id);
  } catch {}
  const shell = element('div','hero-stage');
  const copy = element('div','hero-copy');
  const eyebrow = element('div','hero-eyebrow');
  eyebrow.append(element('span','hero-live-dot'), element('span','','TECNOLOGIA NO SEU RADAR'));
  const heading = element('h1');
  heading.append('Seu próximo upgrade. ', element('span','','Começa aqui.')); 
  copy.append(eyebrow, heading,
    element('p','hero-lede','Do celular ao setup completo: descubra produtos, compare opções e encontre o que combina com você.'));
  const actions = element('div','hero-actions');
  const explore = element('a','hero-primary','Encontrar meu próximo upgrade ↗'); explore.href='#ofertas';
  const guide = element('a','hero-secondary','Me ajude a escolher →'); guide.href='blog/';
  actions.append(explore, guide); copy.append(actions);
  const proof = element('div','hero-proof');
  const count = element('div','hero-proof-item');
  count.append(element('strong','',String(fresh.length)), element('span','','preços conferidos nas últimas 2 horas no catálogo'));
  const rhythm = element('div','hero-proof-item');
  rhythm.append(element('strong','','1 hora'), element('span','','entre as buscas automáticas'));
  proof.append(count,rhythm);
  const disclosure = element('p','hero-disclosure');
  disclosure.append('Links de afiliado. Podemos receber comissão, sem custo adicional. ',
    element('a','','Entenda a transparência ↗'));
  disclosure.querySelector('a').href='transparencia.html';

  const showcase = element('div','hero-showcase');
  const top = element('div','hero-showcase-top');
  top.append(element('span','hero-showcase-label','NA MIRA AGORA'), element('span','hero-showcase-date'));
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

  let index=start;
  const badImages=new Set();
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
    if (badImages.size<slides.length) {
      while (badImages.has(slides[index].id)) index=(index+1)%slides.length;
    }
    const p=slides[index], current=!p.isFeed && MiraQuality.usablePrice(p);
    const discount=current && p.oldPrice>p.price ? Math.floor((1-p.price/p.oldPrice)*100) : 0;
    const date=current ? new Date(p.priceCheck.checkedAt).toLocaleDateString('pt-BR',{timeZone:'America/Sao_Paulo'}) : ''; 
    const image=element('img'); image.src=p.imageUrl; image.alt=p.name;
    image.width=560; image.height=420; image.decoding='async';
    image.addEventListener('error',()=>{
      badImages.add(p.id);
      if (!visual.contains(image)) return;
      visual.classList.add('image-error');
      if (badImages.size<slides.length) move(1);
    },{once:true});
    visual.classList.remove('image-error'); visual.replaceChildren(image,badge);
    badge.hidden=discount<50; badge.textContent=discount+'% OFF';
    category.textContent=p.category || 'Mercado Livre'; title.textContent=p.name;
    old.textContent=current && discount>=50 ? 'De '+money(p.oldPrice) : '';
    price.textContent=p.isFeed
      ? (p.loja === 'Shopee' ? 'A partir de ' : '') + money(p.price)
      : (current ? money(p.price) : 'Consultar preço');
    const listLink = !p.isFeed && isAffiliateList(p);
    link.textContent = p.isFeed ? 'Ver oferta na ' + p.loja + ' ↗'
      : (listLink ? 'Abrir lista na loja ↗' : 'Ver produto na loja ↗');
    link.href=p.offerUrl || p.affiliateUrl; link.target='_blank';
    link.dataset.itemId=p.id; link.dataset.itemName=p.name; link.dataset.itemCategory=p.category || ''; link.dataset.destinationType=listLink ? 'affiliate_list' : 'product';
    status.textContent=p.isFeed ? 'Oferta da ' + p.loja + ' · confirme o valor na loja'
      : (current ? 'Conferido em '+new Date(p.priceCheck.checkedAt).toLocaleString('pt-BR',{timeZone:'America/Sao_Paulo',day:'2-digit',month:'2-digit',hour:'2-digit'}) : 'Preço e disponibilidade na loja');
    top.lastChild.textContent=p.isFeed ? 'PREÇO INFORMADO · CONFIRME' : (current ? 'PREÇO OBSERVADO' : 'CONFIRME NA LOJA');
    position.textContent=(index+1)+' / '+slides.length;
    const previews=slides.map((item,i)=>({item,i})).filter(x=>x.i!==index && !badImages.has(x.item.id));
    controls.hidden=previews.length===0;
    rail.hidden=previews.length===0;
    if (previews.length) {
      const previews=[];
      for (let offset=1; offset<slides.length && previews.length<3; offset++) {
        const target=(index+offset)%slides.length, item=slides[target];
        if (badImages.has(item.id)) continue;
        const button=element('button','hero-rail-item'); button.type='button';
        button.setAttribute('aria-label','Mostrar oferta: '+item.name);
        const thumb=element('img'); thumb.src=item.imageUrl; thumb.alt=''; thumb.loading='lazy';
        thumb.addEventListener('error',()=>{badImages.add(item.id);thumb.replaceWith(element('span','hero-rail-placeholder','↗'));},{once:true});
        const label=element('span'); label.append(element('small','',item.category || 'Oferta'),element('strong','',MiraQuality.usablePrice(item) ? money(item.price) : 'Ver na loja'));
        button.append(thumb,label); button.addEventListener('click',()=>{index=target;render();});
        previews.push(button);
      }
      rail.replaceChildren(...previews);
    }
  }
  function move(direction) {
    if (!slides.length) return;
    let tries=0;
    do {index=(index+direction+slides.length)%slides.length;tries++;}
    while (badImages.has(slides[index].id) && tries<slides.length);
    render();
  }
  previous.addEventListener('click',()=>move(-1));
  next.addEventListener('click',()=>move(1));
  render();
  if (slides.length>1) setInterval(()=>{
    if (!document.hidden && !showcase.matches(':hover') && !showcase.contains(document.activeElement)
      && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) move(1);
  },6500);
  document.addEventListener('mira:catalog-updated', () => {
    const currentId = slides[index]?.id;
    slides = chooseSlides();
    index = Math.max(0, slides.findIndex(p => p.id === currentId));
    render();
  });
  document.addEventListener('visibilitychange', () => { if (!document.hidden) render(); });
  setInterval(()=>{const currentId=slides[index]?.id;slides=chooseSlides();index=Math.max(0,slides.findIndex(p=>p.id===currentId));render();},60000);
})();
