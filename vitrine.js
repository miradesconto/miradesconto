/* Featured cards: verified prices and individual affiliate links from the published catalog. */
(() => {
  'use strict';
  const cards = [...document.querySelectorAll('[data-vitrine-id]')];
  if (!cards.length) return;
  const seeds = cards.map(card => card.dataset.vitrineId);
  const imagesByAffiliate = new Map();
  const validCacheImage = url => typeof url === 'string'
    && /^\/assets\/ofertas\/[a-f0-9]{24}\.(?:jpg|webp|png)$/.test(url);
  function useImage(img, product) {
    const original = img.getAttribute('src');
    const previousLink = img.dataset.affiliateImage;
    const mirrored = imagesByAffiliate.get(product.affiliateUrl)
      || (previousLink === product.affiliateUrl && validCacheImage(original) ? original : null);
    const photo = img.closest('.vitrine-photo');
    const oldFallback = photo?.querySelector('.vitrine-image-unavailable');
    if (oldFallback) oldFallback.remove();
    img.onerror = null;
    img.src = mirrored || product.imageUrl;
    img.dataset.affiliateImage = product.affiliateUrl;
    img.hidden = false;
    img.onerror = function handleBrokenPhoto() {
      img.onerror = null;
      const backup = imagesByAffiliate.get(product.affiliateUrl);
      if (backup && img.getAttribute('src') !== backup) {
        img.src = backup;
      } else {
        img.hidden = true;
        if (photo && !photo.querySelector('.vitrine-image-unavailable')) {
          const label = document.createElement('span');
          label.className = 'vitrine-image-unavailable';
          label.textContent = 'Foto em atualização';
          photo.append(label);
        }
      }
    };
  }

  const money = (n, en) => new Intl.NumberFormat(en ? 'en-US' : 'pt-BR', {style:'currency',currency:'BRL'}).format(n);
  const shortTitle = name => {
    const chars = Array.from(String(name || ''));
    return chars.length > 55 ? chars.slice(0, 52).join('') + '...' : chars.join('');
  };
  const specsFor = p => {
    const explicit = Array.isArray(p.specs) ? p.specs : (typeof p.specs === 'string' ? p.specs.split('|') : []);
    const clean = explicit.map(v => String(v || '').trim().slice(0, 20)).filter(Boolean);
    if (clean.length) return clean.slice(0, 3);

    // Fallback conservador: somente especificações escritas no título.
    const name = p.name || '', specs = [];
    const ryzen = name.match(/\bryzen\s*([3579])\b/i);
    const core = name.match(/\bcore\s*i([3579])\b/i);
    if (ryzen) specs.push('Ryzen ' + ryzen[1]);
    else if (core) specs.push('Core i' + core[1]);
    const ram = name.match(/\b(\d{1,2})\s*GB\s*(?:de\s*)?RAM\b/i);
    if (ram) specs.push(ram[1] + 'GB RAM');
    const ssd = name.match(/\b(\d{3,4})\s*(?:GB)?\s*SSD\b/i);
    if (ssd) specs.push(ssd[1] + 'GB SSD');
    if (specs.length < 3) {
      const hz = name.match(/\b(\d{2,3})\s*Hz\b/i);
      if (hz) specs.push(hz[1] + 'Hz');
    }
    return specs.slice(0, 3);
  };
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
    // Completar IDs indisponíveis apenas com produtos verificados, sem links de lista.
    choices.push(...remaining.slice(0,cards.length-choices.length));

    cards.forEach((card,i) => {
      const p = choices[i], en = card.dataset.locale === 'en';
      card.hidden = !p;
      if (!p) return;
      card.dataset.vitrineId = p.id;
      const img = card.querySelector('.vitrine-photo img');
      useImage(img, p);
      img.alt = p.name;
      const title = card.querySelector('h3');
      title.textContent = shortTitle(p.name);
      title.title = p.name;
      card.querySelector('.vitrine-category').textContent = p.category || (en ? 'Tech' : 'Tecnologia');

      // Na rotação, substituir também as etiquetas para não atribuir specs ao item errado.
      const specs = specsFor(p), box = card.querySelector('[data-specs]');
      if (box) {
        box.replaceChildren(...specs.map(value => {
          const chip = document.createElement('span');
          chip.className = 'vitrine-spec';
          chip.textContent = value;
          return chip;
        }));
        box.hidden = specs.length === 0;
      }

      const price = card.querySelector('[data-price]');
      price.textContent = money(p.price,en);
      price.classList.remove('vitrine-price--missing');
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
      link.dataset.itemId=p.id;
      link.dataset.itemName=p.name;
      link.dataset.itemCategory=p.category || '';
      link.setAttribute('aria-label',(en?'View deal: ':'Ver oferta: ')+p.name);
    });
    window.MiraShowcaseIds = choices.map(p=>p.id);
    const section = cards[0].closest('.vitrine-diaria');
    if (section) section.hidden = choices.length === 0;
    document.dispatchEvent(new CustomEvent('mira:showcase-updated'));
  }
  update();
  // O catálogo já aparece sem rede. Ao receber o feed, priorizar as fotos
  // hospedadas em /assets/ofertas para os cards do destaque.
  fetch('/api/produtos.json', {cache:'no-cache'})
    .then(response => {
      if (!response.ok) throw new Error('Cache de imagens indisponível');
      return response.json();
    })
    .then(rows => {
      if (!Array.isArray(rows)) return;
      rows.forEach(row => {
        if (validCacheImage(row?.imagem) && typeof row.link_afiliado === 'string') {
          imagesByAffiliate.set(row.link_afiliado, row.imagem);
        }
      });
      update();
    })
    .catch(() => { /* O HTML/Jekyll e as imagens originais permanecem disponíveis. */ });
  document.addEventListener('mira:catalog-updated',update);
  setInterval(update,60000);
})();
