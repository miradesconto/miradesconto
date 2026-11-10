/* MiraDesconto: fotos locais verificadas, Shopee como prioridade, reserva Jekyll sem rede. */
(() => {
  'use strict';
  const section = document.getElementById('auto-ofertas');
  const grid = section && section.querySelector('[data-auto-grid]');
  const notice = document.getElementById('auto-offers-status');
  if (!section || !grid) return;

  const currency = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
  const make = (tag, className, value) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (value !== undefined) node.textContent = value;
    return node;
  };

  function validImage(url) {
    if (typeof url !== 'string') return false;
    if (/^\/assets\/ofertas\/[a-f0-9]{24}\.(?:jpg|png|webp)$/.test(url)) return true;
    try {
      const u = new URL(url);
      return u.protocol === 'https:' && ['cf.shopee.com.br', 'down-br.img.susercontent.com',
        'down-bs-br.img.susercontent.com', 'http2.mlstatic.com'].includes(u.hostname);
    } catch (_) { return false; }
  }

  function validAffiliate(link, loja) {
    try {
      const u = new URL(link);
      if (u.protocol !== 'https:' || u.username || u.password) return false;
      if (loja === 'Shopee') return u.hostname === 's.shopee.com.br';
      if (loja === 'Mercado Livre') return u.hostname === 'meli.la'
        || ((u.hostname === 'mercadolivre.com.br' || u.hostname.endsWith('.mercadolivre.com.br'))
          && u.searchParams.has('matt_tool_id'));
    } catch (_) {}
    return false;
  }

  function eligible(p) {
    return p && typeof p.titulo === 'string' && p.titulo.trim()
      && Number.isFinite(Number(p.preco_atual)) && Number(p.preco_atual) > 0
      && ['Shopee', 'Mercado Livre'].includes(p.loja)
      && validImage(p.imagem) && validAffiliate(p.link_afiliado, p.loja);
  }

  const candidates = url => {
    const options = [url];
    if (url.startsWith('https://cf.shopee.com.br/file/')) {
      const path = url.slice('https://cf.shopee.com.br'.length);
      options.push('https://down-br.img.susercontent.com' + path,
        'https://down-bs-br.img.susercontent.com' + path);
    }
    return options;
  };

  function resilientPhoto(img) {
    // Prefere imagens do próprio domínio. Em CDN externo tenta hosts oficiais alternativos.
    let queue = candidates(img.src);
    let attempt = 0;
    img.addEventListener('error', () => {
      attempt += 1;
      if (attempt < queue.length) {
        img.src = queue[attempt];
        return;
      }
      img.hidden = true;
      const wrap = img.closest('.auto-photo');
      if (wrap && !wrap.querySelector('.auto-image-fallback')) {
        const fallback = make('span', 'auto-image-fallback', 'Foto em atualização');
        fallback.setAttribute('role', 'img');
        fallback.setAttribute('aria-label', 'Imagem indisponível para este produto');
        wrap.append(fallback);
      }
    });
  }

  function card(p, index) {
    const article = make('article', 'auto-card');
    const photo = make('div', 'auto-photo');
    const img = document.createElement('img');
    img.src = p.imagem;
    img.alt = p.titulo;
    img.width = 400;
    img.height = 300;
    img.loading = index < 4 ? 'eager' : 'lazy';
    img.decoding = 'async';
    resilientPhoto(img);
    photo.append(img);
    const body = make('div', 'auto-body');
    body.append(make('span', 'auto-store', p.loja));
    const title = make('h3', 'auto-title', p.titulo.length > 55
      ? Array.from(p.titulo).slice(0, 52).join('') + '...' : p.titulo);
    title.title = p.titulo;
    body.append(title);
    body.append(make('strong', 'auto-price',
      (p.loja === 'Shopee' ? 'A partir de ' : '') + currency.format(Number(p.preco_atual))));
    body.append(make('p', 'auto-note', 'Confirme preço e disponibilidade na loja'));
    const link = make('a', 'auto-cta', 'Ver Oferta ↗');
    link.href = p.link_afiliado;
    link.target = '_blank';
    link.rel = 'sponsored nofollow noopener noreferrer';
    link.dataset.itemName = p.titulo;
    link.dataset.itemCategory = 'Ofertas automáticas';
    link.dataset.linkLocation = 'auto-showcase';
    link.dataset.destinationType = 'product';
    link.setAttribute('aria-label', 'Ver oferta: ' + p.titulo);
    body.append(link);
    body.append(make('small', 'auto-disclosure', 'Link de afiliado · valores em reais'));
    article.append(photo, body);
    return article;
  }

  // Os cards estáticos funcionam sem JS; adicionamos proteção para foto quebrada.
  grid.querySelectorAll('[data-auto-server-card] img').forEach(resilientPhoto);

  async function loadOffers() {
    try {
      const response = await fetch('/api/produtos.json', { cache: 'no-store' });
      if (!response.ok) throw new Error('Feed HTTP ' + response.status);
      const data = await response.json();
      if (!Array.isArray(data)) throw new Error('Feed não é lista');
      const seen = new Set();
      const priorMainLinks = new Set([...document.querySelectorAll('.vitrine-cta[href]')].map(a => a.href));
      const eligibleRows = data.filter(eligible).filter(p => {
        if (seen.has(p.link_afiliado) || priorMainLinks.has(p.link_afiliado)) return false;
        seen.add(p.link_afiliado);
        return true;
      });
      // Até seis Shopee e dois Mercado Livre, sem excluir Shopee quando API cai.
      const shop = eligibleRows.filter(p => p.loja === 'Shopee');
      const ml = eligibleRows.filter(p => p.loja === 'Mercado Livre');
      const picks = [...shop.slice(0, 6), ...ml.slice(0, 2)].slice(0, 8);
      if (!picks.length) throw new Error('Sem itens válidos');
      grid.replaceChildren(...picks.map(card));
      section.hidden = false;
      if (notice) notice.hidden = true;
    } catch (_) {
      // Falha do fetch: manter a vitrine Jekyll com links Shopee confirmados.
      if (grid.children.length === 0 && notice) {
        notice.textContent = 'As ofertas estão sendo atualizadas. Confira também as ofertas em destaque acima.';
        notice.hidden = false;
      }
    }
  }

  loadOffers();
})();