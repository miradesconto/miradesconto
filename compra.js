'use strict';
(() => {
  const products = window.MIRA_DATA?.products || [];
  const cards = document.querySelectorAll('[data-product-id]');
  function refresh() {
    for (const card of cards) {
      const product = products.find(p => p.id === card.dataset.productId);
      const price = card.querySelector('[data-price]');
      if (!product || !MiraQuality.usablePrice(product)) {
        price.textContent = 'Preço atual a confirmar na loja.';
      } else {
        const checked = new Date(product.priceCheck.checkedAt).toLocaleString('pt-BR', {timeZone:'America/Sao_Paulo'});
        price.textContent = product.price.toLocaleString('pt-BR', {style:'currency', currency:'BRL'}) + ' · Verificado em ' + checked + ' (Brasília).';
      }
    }
  }
  for (const card of cards) {
    const product = products.find(p => p.id === card.dataset.productId);
    const history = card.querySelector('[data-history]');
    if (product && window.MiraHistory) {
      history.hidden = false;
      history.addEventListener('click', () => window.MiraHistory.open(product, history));
    }
  }
  refresh();
  setInterval(refresh, 60000);
})();
