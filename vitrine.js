/* Featured cards: use only verified prices and individual affiliate links from the published catalog. */
(() => {
  'use strict';
  const cards = [...document.querySelectorAll('[data-vitrine-id]')];
  if (!cards.length) return;
  const seeds = cards.map(card => card.dataset.vitrineId);
  const money = (n, en) => new Intl.NumberFormat(en ? 'en-US' : 'pt-BR', {style:'currency',currency:'BRL'}).format(n);
  const approved = p => p && p.available !== false && p.name && p.imageUrl
    && /^https:\/\/meli\.la\/[A-Za-z0-9]+$/.test(p.affiliateUrl || '')
    && p.affiliateUrl !== 'https://meli.la/1NguveN' && p.affiliateUrl !== 'https://meli.la/1pyBZm8'
    && p.affiliateLinkType !== 'list' && window.MiraQuality?.usablePrice(p) === true;
  function update() {
    const catalog = (window.MIRA_DATA?.products || []).filter(approved);
    const choices = [];
    const byId = new Map(catalog.map(p => [p.id,p]));
    seeds.forEach(id => {const p = byId.get(id);if(p && choices.length<cards.length)choices.push(p);});
    const remaining = catalog.filter(p => !choices.includes(p)).sort((a,b) => Number(b.featured===true)-Number(a.featured===true)
      || ((b.oldPrice>b.price ? (1-b.price/b.oldPrice) : 0) - (a.oldPrice>a.price ? (1-a.price/a.oldPrice) : 0))
      || a.id.localeCompare(b.id));
    // Fill missing curated IDs with fresh verified, affiliate-linked products instead of stale cards.
    choices.push(...remaining.slice(0,cards.length-choices.length));
    cards.forEach((card,i) => {
      const p = choices[i], en = card.dataset.locale === 'en';
      card.hidden = !p;
      if (!p) return;
      card.dataset.vitrineId = p.id;
      const img = card.querySelector('.vitrine-photo img');
      img.src = p.imageUrl; img.alt = p.name;
      card.querySelector('h3').textContent = p.name;
      card.querySelector('.vitrine-category').textContent = p.category || (en ? 'Tech' : 'Tecnologia');
      card.querySelector('[data-price]').textContent = money(p.price,en);
      const old = card.querySelector('[data-old]');
      const discounted = Number.isFinite(p.oldPrice) && p.oldPrice>p.price;
      old.hidden = !discounted;
      old.textContent = discounted ? money(p.oldPrice,en) : '';
      const hot = card.querySelector('[data-hot]');
      hot.hidden = !discounted || (1-p.price/p.oldPrice)<0.15;
      const checked = new Date(p.priceCheck.checkedAt).toLocaleString(en ? 'en-US':'pt-BR',{timeZone:'America/Sao_Paulo'});
      card.querySelector('[data-checked]').textContent = (en?'Checked: ':'Conferido em ')+checked+' (Brasília)';
      const link = card.querySelector('.vitrine-cta');
      link.href=p.affiliateUrl;
      link.dataset.itemId=p.id;link.dataset.itemName=p.name;link.dataset.itemCategory=p.category || '';
    });
    window.MiraShowcaseIds = choices.map(p=>p.id);
    const section = cards[0].closest('.vitrine-diaria');
    if (section) section.hidden = choices.length === 0;
    document.dispatchEvent(new CustomEvent('mira:showcase-updated'));
  }
  update();
  document.addEventListener('mira:catalog-updated',update);
  setInterval(update,60000);
})();
