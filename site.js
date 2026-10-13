'use strict';
(() => {
  let articles = [];
  try { articles = JSON.parse(document.getElementById('editorial-data')?.textContent || '[]'); } catch { return; }
  const byProduct = new Map();
  for (const article of articles) {
    if (typeof article.url !== 'string' || !article.url.startsWith('/blog/')) continue;
    for (const id of article.ids || []) if (!byProduct.has(id)) byProduct.set(id, article);
  }
  window.MiraEditorial = {find: id => byProduct.get(id)};
  function connectCards(root = document) {
    root.querySelectorAll('.card[data-id],.radar-card[data-product-id]').forEach(card => {
      if (card.querySelector('.card-editorial-link')) return;
      const article = byProduct.get(card.dataset.id || card.dataset.productId);
      if (!article || card.querySelector(`a[href="${article.url}"]`)) return;
      const link = document.createElement('a');
      link.className = 'card-editorial-link'; link.href = article.url;
      link.textContent = 'Ler sobre este produto →';
      link.setAttribute('aria-label', 'Ler: ' + article.title);
      const body = card.querySelector('.card-content,.radar-card-body');
      const actions = body?.querySelector('.buttons,.radar-actions');
      if (body) body.insertBefore(link, actions || null);
    });
  }
  connectCards();
  const radarBox = document.querySelector('[data-radar-product]');
  if (radarBox) {
    let insight = {checkedAt:radarBox.dataset.checkedAt};
    const expire = () => { radarBox.hidden = !window.MiraRadar.fresh(insight); };
    async function refreshInsight() {
      expire();
      if (document.hidden) return;
      try {
        const response = await fetch('/radar/feed.json', {cache:'no-store'});
        if (!response.ok) return;
        const feed = await response.json();
        const next = feed.byId?.[radarBox.dataset.radarProduct];
        if (!next) { radarBox.hidden = true; insight = {}; return; }
        insight = next;
        radarBox.querySelector('strong').textContent = next.label;
        radarBox.querySelector('p').textContent = `${next.currentPriceText} · ${next.reason} Base: ${next.periodText}.`;
        expire();
      } catch { expire(); }
    }
    refreshInsight(); setInterval(expire,60000); setInterval(refreshInsight,5 * 60000);
    document.addEventListener('visibilitychange', () => {if (!document.hidden) refreshInsight();});
  }
  for (const root of document.querySelectorAll('#productList,#radarGrid')) {
    new MutationObserver(() => connectCards(root)).observe(root, {childList:true});
  }
  const search = document.getElementById('editorialSearch');
  if (search) {
    const normalize = value => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
    const cards = [...document.querySelectorAll('.editorial-card-clean')];
    search.addEventListener('input', () => {
      const words = normalize(search.value).trim().split(/\s+/).filter(Boolean);
      let count = 0;
      for (const card of cards) {
        card.hidden = !words.every(word => normalize(card.textContent).includes(word));
        if (!card.hidden) count++;
      }
      document.querySelectorAll('.editorial-lane').forEach(lane => {
        lane.hidden = ![...lane.querySelectorAll('.editorial-card-clean')].some(card => !card.hidden);
      });
      document.getElementById('editorialSearchStatus').textContent = words.length ? `${count} conteúdo${count === 1 ? '' : 's'} encontrado${count === 1 ? '' : 's'}.` : '';
    });
  }
})();
