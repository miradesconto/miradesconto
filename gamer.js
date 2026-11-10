/* MiraDesconto Gamer: mesma fonte /api/produtos.json, apresentação independente. */
(() => {
  'use strict';

  const grid = document.getElementById('vitrine-produtos');
  const count = document.getElementById('gamer-count');
  const status = document.getElementById('gamer-status');
  const total = document.getElementById('gamer-total');
  const more = document.getElementById('gamer-more');
  const search = document.getElementById('gamer-search');
  const store = document.getElementById('gamer-store');
  const sort = document.getElementById('gamer-sort');
  if (![grid, count, status, total, more, search, store, sort].every(Boolean)) return;

  const PRICE = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
  const PAGE_SIZE = 12;
  let items = [];
  let visibleCount = PAGE_SIZE;

  function element(tag, className, value) {
    const e = document.createElement(tag);
    if (className) e.className = className;
    if (value !== undefined) e.textContent = value;
    return e;
  }

  function secureHttps(raw) {
    if (typeof raw !== 'string') return null;
    try {
      const url = new URL(raw);
      return url.protocol === 'https:' && !url.username && !url.password ? url : null;
    } catch (_) {
      return null;
    }
  }

  function affiliateUrl(raw, loja) {
    const url = secureHttps(raw);
    if (!url) return null;
    const host = url.hostname.toLowerCase();
    if (loja === 'Shopee') return host === 's.shopee.com.br' ? url.href : null;
    if (loja === 'Mercado Livre') {
      if (host === 'meli.la') return url.href;
      if ((host === 'mercadolivre.com.br' || host.endsWith('.mercadolivre.com.br'))
          && url.searchParams.has('matt_tool_id')) return url.href;
    }
    return null;
  }

  function normalize(item) {
    if (!item || typeof item !== 'object') return null;
    const title = typeof item.titulo === 'string' ? item.titulo.trim() : '';
    const price = Number(item.preco_atual);
    const loja = item.loja;
    const image = secureHttps(item.imagem);
    const href = affiliateUrl(item.link_afiliado, loja);
    if (!title || !Number.isFinite(price) || price <= 0 || price > 1e6 ||
        !image || !href || !['Mercado Livre', 'Shopee'].includes(loja)) return null;
    return { title, price, loja, image: image.href, href };
  }

  function createCard(item, index) {
    const card = element('article', 'gamer-card');
    const picture = element('div', 'gamer-photo');
    const image = document.createElement('img');
    image.src = item.image;
    image.alt = item.title;
    image.width = 400;
    image.height = 300;
    image.loading = index < 4 ? 'eager' : 'lazy';
    image.decoding = 'async';
    picture.append(image);

    const body = element('div', 'gamer-card-content');
    body.append(element('span', 'gamer-store', item.loja));
    const heading = element('h3', 'gamer-product-title', item.title);
    heading.title = item.title;
    body.append(heading);

    const price = element('div', 'gamer-price');
    price.append(element('small', '', item.loja === 'Shopee' ? 'Preço a partir de' : 'Preço informado'));
    price.append(element('span', '', PRICE.format(item.price)));
    body.append(price);

    const link = element('a', 'gamer-cta', 'VER OFERTA');
    link.href = item.href;
    link.target = '_blank';
    link.rel = 'sponsored nofollow noopener noreferrer';
    link.dataset.itemName = item.title;
    link.dataset.itemCategory = 'Ofertas automáticas';
    link.dataset.linkLocation = 'gamer-showcase';
    link.dataset.destinationType = 'product';
    link.setAttribute('aria-label', 'Ver oferta de ' + item.title + ' na ' + item.loja);
    body.append(link);
    body.append(element('small', 'gamer-affiliate-label', 'Link de afiliado · confirme o valor na loja'));

    card.append(picture, body);
    return card;
  }

  function simplify(s) {
    return String(s).normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  }

  function currentItems() {
    const term = simplify(search.value.trim());
    const origin = store.value;
    const filtered = items.filter(p => (origin === 'all' || origin === p.loja)
      && (!term || simplify(p.title + ' ' + p.loja).includes(term)));
    if (sort.value === 'price-asc') filtered.sort((a, b) => a.price - b.price);
    if (sort.value === 'price-desc') filtered.sort((a, b) => b.price - a.price);
    return filtered;
  }

  function render() {
    const filtered = currentItems();
    const visible = filtered.slice(0, visibleCount);
    const fragment = document.createDocumentFragment();
    visible.forEach((p, i) => fragment.append(createCard(p, i)));
    grid.replaceChildren(fragment);
    count.textContent = filtered.length
      ? filtered.length + ' ofertas encontradas · ' + visible.length + ' exibidas'
      : 'Nenhuma oferta corresponde aos filtros';
    more.hidden = filtered.length <= visibleCount;
    status.hidden = filtered.length !== 0;
    status.textContent = filtered.length ? '' : 'Nenhum produto encontrado. Tente outra busca ou loja.';
  }

  [search, store, sort].forEach(control => control.addEventListener(
    control === search ? 'input' : 'change',
    () => { visibleCount = PAGE_SIZE; render(); }
  ));
  more.addEventListener('click', () => { visibleCount += PAGE_SIZE; render(); });

  async function load() {
    grid.setAttribute('aria-busy', 'true');
    try {
      const response = await fetch('/api/produtos.json', { cache: 'no-store' });
      if (!response.ok) throw new Error('Falha HTTP ' + response.status);
      const data = await response.json();
      if (!Array.isArray(data)) throw new Error('Feed inválido');
      const seen = new Set();
      items = data.map(normalize).filter(Boolean).filter(p => {
        if (seen.has(p.href)) return false;
        seen.add(p.href);
        return true;
      });
      if (!items.length) throw new Error('Sem ofertas válidas');
      total.textContent = String(items.length);
      render();
    } catch (_) {
      count.textContent = 'Ofertas temporariamente indisponíveis';
      status.textContent = 'Estamos atualizando as ofertas. Consulte novamente em instantes.';
      status.hidden = false;
      more.hidden = true;
    } finally {
      grid.setAttribute('aria-busy', 'false');
    }
  }

  load();
})();