/* Add an Offer only when the existing two-hour verification policy passes.
   The static Product JSON-LD remains valid without a current Offer. */
(() => {
  'use strict';
  function updateSchema() {
    const el = document.getElementById('mira-product-jsonld');
    if (!el) return;
    let base;
    try { base = JSON.parse(el.textContent); } catch { return; }
    const id = base.sku;
    if (!id) return;
    const p = (window.MIRA_DATA?.products || []).find(item => item.id === id);
    delete base.offers;
    if (p && window.MiraQuality?.usablePrice(p) === true && /^https:\/\//.test(p.affiliateUrl || '')) {
      const offer = {'@type':'Offer', 'url':p.affiliateUrl, 'priceCurrency':'BRL', 'price':p.price, 'seller':{'@type':'Organization', 'name':p.store || 'Mercado Livre'}};
      if (p.available === true) offer.availability = 'https://schema.org/InStock';
      base.offers = offer;
    }
    el.textContent = JSON.stringify(base);
  }
  document.addEventListener('DOMContentLoaded', updateSchema);
  document.addEventListener('mira:catalog-updated', updateSchema);
  setInterval(updateSchema, 60000);
})();
