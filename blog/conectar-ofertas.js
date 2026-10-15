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
      const body = card.querySelector('.card-content');
      if (!body) continue;
      // interface.js may already add a buying analysis. Keep that link and
      // never stack a second editorial destination over the purchase button.
      const existing = [...body.querySelectorAll('a.product-link')];
      if (existing.length) {
        existing.slice(1).forEach(link => link.remove());
        continue;
      }
      const entry = byId.get(card.dataset.id);
      if (!entry) continue;
      const buttons = body.querySelector('.buttons');
      if (!buttons) continue;
      const link = document.createElement('a');
      link.className = 'product-link product-editorial-link';
      link.href = entry.url; link.textContent = 'Vale a pena? Veja o guia →';
      link.setAttribute('aria-label', 'Ler: ' + entry.title);
      body.insertBefore(link, buttons);
    }
  }
  connect();
  new MutationObserver(connect).observe(grid, {childList:true});
})();
