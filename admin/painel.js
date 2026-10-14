'use strict';
(() => {
  const elements = {
    total: document.getElementById('total'),
    vitrine: document.getElementById('vitrine'),
    recentes: document.getElementById('recentes'),
    pendentes: document.getElementById('pendentes'),
    busca: document.getElementById('busca'),
    filtro: document.getElementById('filtro'),
    grade: document.getElementById('grade'),
    resultado: document.getElementById('resultado'),
    recarregar: document.getElementById('recarregar'),
    detalhes: document.getElementById('detalhes'),
    nome: document.getElementById('detalhe-nome'),
    situacao: document.getElementById('detalhe-status'),
    id: document.getElementById('detalhe-id'),
    preco: document.getElementById('detalhe-preco'),
    data: document.getElementById('detalhe-data'),
    publicacao: document.getElementById('detalhe-publicacao'),
    link: document.getElementById('detalhe-link'),
    copiar: document.getElementById('copiar-link'),
    abrir: document.getElementById('abrir-link'),
    fechar: document.getElementById('fechar-detalhes')
  };
  const MAX_CARDS = 30;
  const PRICE_AGE_MS = 24 * 60 * 60 * 1000;
  const CLOCK_TOLERANCE_MS = 5 * 60 * 1000;
  let products = [];
  let published = new Set();
  let selected = null;
  let catalogLoaded = false;
  const currency = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
  const validAffiliate = url => typeof url === 'string' &&
    /^https:\/\/(?:meli\.la\/[A-Za-z0-9]+|(?:www\.)?mercadolivre\.com(?:\.br)?\/sec\/[A-Za-z0-9]+)$/.test(url);

  function priceEvidence(item, now = Date.now()) {
    const proof = item && item.priceCheck;
    if (!proof || proof.status !== 'verified' || proof.currency !== 'BRL' ||
        proof.itemId !== item.id || !Number.isFinite(proof.price) ||
        !Number.isFinite(item.price) || item.price <= 0 ||
        Math.abs(proof.price - item.price) > 0.011 ||
        typeof proof.checkedAt !== 'string') return null;
    const time = Date.parse(proof.checkedAt);
    if (!Number.isFinite(time) || time > now + CLOCK_TOLERANCE_MS ||
        now - time > PRICE_AGE_MS) return null;
    return { time, price: item.price };
  }

  function verifiedDiscount(item) {
    const old = item.oldPrice;
    const proof = item.priceCheck;
    return Boolean(proof && Number.isFinite(old) && old > item.price &&
      Number.isFinite(proof.oldPrice) && Math.abs(proof.oldPrice - old) <= 0.011);
  }

  function validImage(url) {
    if (typeof url !== 'string') return false;
    try {
      const parsed = new URL(url);
      return parsed.protocol === 'https:' && parsed.hostname.endsWith('.mlstatic.com');
    } catch { return false; }
  }

  function prettyTime(ms) {
    return new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short',
      timeZone: 'America/Sao_Paulo' }).format(new Date(ms)) + ' (Brasília)';
  }

  function productStatus(item) {
    if (!priceEvidence(item)) return { label: 'Preço pendente', className: 'pendente' };
    return { label: 'Preço confirmado em 24h', className: '' };
  }

  function clearDetails() {
    selected = null;
    elements.detalhes.hidden = true;
  }

  function showDetails(item) {
    selected = item.id;
    elements.detalhes.hidden = false;
    elements.nome.textContent = item.name;
    elements.id.textContent = item.id;
    elements.publicacao.textContent = published.has(item.id) ? 'Na vitrine' : 'Fora da vitrine';
    const verified = priceEvidence(item);
    elements.situacao.textContent = verified ?
      'Este preço tem evidência recente associada ao anúncio exato.' :
      'O sistema não possui comprovação de preço recente para este anúncio.';
    elements.preco.textContent = verified ? currency.format(verified.price) +
      (verifiedDiscount(item) ? ' · Antes: ' + currency.format(item.oldPrice) : '') :
      'Consultar diretamente na loja';
    elements.data.textContent = verified ? prettyTime(verified.time) :
      'Sem confirmação válida nas últimas 24 horas';
    const url = validAffiliate(item.affiliateUrl) ? item.affiliateUrl : '';
    elements.link.value = url;
    elements.copiar.disabled = !url;
    elements.abrir.hidden = !url;
    if (url) {
      elements.abrir.href = url;
    } else {
      elements.abrir.removeAttribute('href');
    }
    elements.detalhes.scrollIntoView({ block: 'nearest' });
  }

  function makeCard(item) {
    const card = document.createElement('button');
    card.type = 'button';
    card.className = 'produto';
    card.setAttribute('role', 'listitem');
    card.setAttribute('aria-pressed', selected === item.id ? 'true' : 'false');
    if (validImage(item.imageUrl)) {
      const img = document.createElement('img');
      img.src = item.imageUrl;
      img.alt = '';
      img.loading = 'lazy';
      img.addEventListener('error', () => {
        const fallback = document.createElement('span');
        fallback.className = 'sem-imagem';
        fallback.textContent = 'Sem foto';
        img.replaceWith(fallback);
      }, { once: true });
      card.append(img);
    } else {
      const fallback = document.createElement('span');
      fallback.className = 'sem-imagem';
      fallback.textContent = 'Sem foto';
      card.append(fallback);
    }
    const info = document.createElement('span');
    info.className = 'produto-texto';
    const title = document.createElement('strong');
    title.textContent = item.name;
    const id = document.createElement('small');
    id.textContent = item.id + (published.has(item.id) ? ' · Vitrine' : ' · Acervo');
    const status = document.createElement('span');
    const state = productStatus(item);
    status.className = 'selo ' + state.className;
    status.textContent = state.label;
    info.append(title, id, status);
    card.append(info);
    card.addEventListener('click', () => {
      showDetails(item);
      renderCards();
    });
    return card;
  }

  function renderSummary() {
    const inStore = products.filter(p => published.has(p.id));
    const fresh = inStore.filter(p => priceEvidence(p)).length;
    elements.total.textContent = products.length.toLocaleString('pt-BR');
    elements.vitrine.textContent = inStore.length.toLocaleString('pt-BR');
    elements.recentes.textContent = fresh.toLocaleString('pt-BR');
    elements.pendentes.textContent = (inStore.length - fresh).toLocaleString('pt-BR');
  }

  function matchesFilter(item, choice) {
    switch (choice) {
      case 'publicados': return published.has(item.id);
      case 'nao-publicados': return !published.has(item.id);
      case 'recentes': return Boolean(priceEvidence(item));
      case 'pendentes': return !priceEvidence(item);
      case 'sem-afiliado': return !validAffiliate(item.affiliateUrl);
      default: return true;
    }
  }

  function renderCards() {
    if (!catalogLoaded) return;
    const term = elements.busca.value.trim().toLocaleLowerCase('pt-BR');
    const matches = products.filter(item =>
      matchesFilter(item, elements.filtro.value) &&
      (!term || (item.name + ' ' + item.id + ' ' + (item.category || '')).toLocaleLowerCase('pt-BR').includes(term))
    );
    const fragment = document.createDocumentFragment();
    for (const item of matches.slice(0, MAX_CARDS)) fragment.append(makeCard(item));
    elements.grade.replaceChildren(fragment);
    elements.grade.setAttribute('aria-busy', 'false');
    elements.resultado.textContent = matches.length ?
      'Exibindo ' + Math.min(matches.length, MAX_CARDS) + ' de ' + matches.length +
      ' produtos encontrados. Clique em um produto para ver os detalhes.' :
      'Nenhum produto corresponde aos filtros.';
    if (selected && !matches.some(x => x.id === selected)) clearDetails();
  }

  async function loadCatalog() {
    elements.recarregar.disabled = true;
    elements.grade.setAttribute('aria-busy', 'true');
    elements.resultado.textContent = 'Consultando o catálogo...';
    try {
      const response = await fetch('../dados/catalogo.json', { cache: 'no-store' });
      if (!response.ok) throw new Error('HTTP ' + response.status);
      const data = await response.json();
      if (!data || !Array.isArray(data.products) || !Array.isArray(data.publishedIds))
        throw new Error('Estrutura do catálogo não reconhecida');
      const rows = data.products.filter(p => p && /^MLB\d{7,}$/.test(p.id) && typeof p.name === 'string');
      const seen = new Set();
      products = rows.filter(p => {
        if (seen.has(p.id)) return false;
        seen.add(p.id);
        return true;
      });
      published = new Set(data.publishedIds);
      catalogLoaded = true;
      clearDetails();
      renderSummary();
      renderCards();
    } catch (error) {
      catalogLoaded = false;
      clearDetails();
      elements.grade.replaceChildren();
      elements.grade.setAttribute('aria-busy', 'false');
      elements.resultado.textContent = 'Não foi possível carregar o catálogo. Confira a conexão e tente novamente. (' + error.message + ')';
    } finally {
      elements.recarregar.disabled = false;
    }
  }

  elements.busca.addEventListener('input', renderCards);
  elements.filtro.addEventListener('change', renderCards);
  elements.recarregar.addEventListener('click', loadCatalog);
  elements.fechar.addEventListener('click', () => { clearDetails(); renderCards(); });
  elements.copiar.addEventListener('click', async () => {
    if (!elements.link.value) return;
    try {
      await navigator.clipboard.writeText(elements.link.value);
      elements.situacao.textContent = 'Link cadastrado copiado. Confira a atribuição no programa de afiliados.';
    } catch {
      elements.link.focus();
      elements.link.select();
      elements.situacao.textContent = 'Selecione e copie o link exibido no campo.';
    }
  });
  elements.grade.parentNode.insertBefore(elements.detalhes, elements.grade);
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden && catalogLoaded) {
      renderSummary();
      if (selected) {
        const product = products.find(p => p.id === selected);
        if (product) showDetails(product);
      }
      renderCards();
    }
  });
  setInterval(() => {
    if (catalogLoaded && !document.hidden) {
      renderSummary();
      renderCards();
    }
  }, 60_000);
  loadCatalog();
})();
