'use strict';
(() => {
  const grid = document.getElementById('productList');
  if (!grid) return;
  let entries;
  try { entries = JSON.parse(document.getElementById('editorial-data').textContent); } catch { return; }
  const byId = new Map();
  // Prefer focused articles, then broader guides; only published pages are emitted.
  entries.sort((a,b) => a.ids.length - b.ids.length);
  for (const entry of entries) {
    if (!entry.url.startsWith('/blog/')) continue;
    for (const id of entry.ids) if (!byId.has(id)) byId.set(id, entry);
  }
  function connect() {
    for (const card of grid.querySelectorAll('.card[data-id]')) {
      if (card.querySelector('.product-editorial-link')) continue;
      const entry = byId.get(card.dataset.id);
      if (!entry) continue;
      const link = document.createElement('a');
      link.className = 'product-link product-editorial-link';
      link.href = entry.url; link.textContent = 'Vale a pena? Veja o guia →';
      link.setAttribute('aria-label', 'Ler: ' + entry.title);
      const body = card.querySelector('.card-content');
      body?.insertBefore(link, body.querySelector('.buttons'));
    }
  }
  connect();
  new MutationObserver(connect).observe(grid, {childList:true});
})();
