/* MiraDesconto: vitrine automática do feed api/produtos.json, sem chaves no navegador. */
(() => {
  'use strict';
  const root = document.getElementById('auto-ofertas');
  const grid = root && root.querySelector('[data-auto-grid]');
  if (!grid) return;

  const valid = item => item
    && typeof item.titulo === 'string' && item.titulo.trim()
    && Number.isFinite(Number(item.preco_atual)) && Number(item.preco_atual) > 0
    && ['Shopee', 'Mercado Livre'].includes(item.loja)
    && /^https:\/\//i.test(item.imagem || '')
    && /^https:\/\//i.test(item.link_afiliado || '');
  const money = new Intl.NumberFormat('pt-BR', {style:'currency', currency:'BRL'});
  const create = (tag, cls, text) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const render = item => {
    const card = create('article','auto-card');
    const photo = create('div','auto-photo');
    const img = document.createElement('img');
    img.src = item.imagem;
    img.alt = item.titulo;
    img.loading = 'lazy';
    img.decoding = 'async';
    img.width = 400;
    img.height = 300;
    photo.append(img);
    card.append(photo);

    const body = create('div','auto-body');
    body.append(create('span','auto-store',item.loja));
    const title = create('h3','auto-title',item.titulo.length > 55 ? item.titulo.slice(0,52)+'...' : item.titulo);
    title.title = item.titulo;
    body.append(title);
    body.append(create('strong','auto-price',(item.loja === 'Shopee' ? 'A partir de ' : '')+money.format(Number(item.preco_atual))));
    body.append(create('p','auto-note','Confirme preço e disponibilidade na loja'));
    const link = create('a','auto-cta','Ver Oferta ↗');
    link.href = item.link_afiliado;
    link.target = '_blank';
    link.rel = 'sponsored nofollow noopener noreferrer';
    link.dataset.itemName = item.titulo;
    link.dataset.itemCategory = 'Ofertas automáticas';
    link.dataset.linkLocation = 'auto-showcase';
    link.dataset.destinationType = 'product';
    link.setAttribute('aria-label','Ver oferta: '+item.titulo);
    body.append(link);
    body.append(create('small','auto-disclosure','Link de afiliado · valores em reais'));
    card.append(body);
    return card;
  };

  fetch('/api/produtos.json', {cache:'no-cache'})
    .then(response => { if (!response.ok) throw new Error('feed indisponível'); return response.json(); })
    .then(items => {
      if (!Array.isArray(items)) return;
      const seen = new Set([...document.querySelectorAll('.vitrine-cta[href]')].map(a=>a.href));
      const curated = items.filter(valid).filter(item => {
        if (seen.has(item.link_afiliado)) return false;
        seen.add(item.link_afiliado);
        return true;
      }).slice(0, 4);
      if (!curated.length) return;
      grid.replaceChildren(...curated.map(render));
      root.hidden = false;
    })
    .catch(() => { root.hidden = true; });
})();
