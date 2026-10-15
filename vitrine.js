/* Progressive enhancement: never claim an expired price or an unverified discount. */
(() => {
  'use strict';
  const cards = [...document.querySelectorAll('[data-vitrine-id]')];
  if (!cards.length) return;
  const money = (n, en) => new Intl.NumberFormat(en ? 'en-US' : 'pt-BR', {style:'currency', currency:'BRL'}).format(n);
  function update() {
    const catalog = window.MIRA_DATA?.products || [];
    cards.forEach(card => {
      const p = catalog.find(item => item.id === card.dataset.vitrineId);
      const en = card.dataset.locale === 'en';
      const valid = p && window.MiraQuality?.usablePrice(p) === true;
      const price = card.querySelector('[data-price]');
      const old = card.querySelector('[data-old]');
      const hot = card.querySelector('[data-hot]');
      const checked = card.querySelector('[data-checked]');
      price.textContent = valid ? money(p.price, en) : (en ? 'Check price at store' : 'Consultar preço na loja');
      const discounted = valid && Number.isFinite(p.oldPrice) && p.oldPrice > p.price;
      old.hidden = !discounted;
      if (discounted) old.textContent = money(p.oldPrice, en);
      const pct = discounted ? Math.round((1-p.price/p.oldPrice)*100) : 0;
      hot.hidden = pct < 15;
      checked.textContent = valid
        ? (en ? 'Last checked: ' : 'Conferido em ') + new Date(p.priceCheck.checkedAt).toLocaleString(en ? 'en-US' : 'pt-BR', {timeZone:'America/Sao_Paulo'}) + ' (BRT)'
        : (en ? 'Price and availability at store' : 'Preço e disponibilidade na loja');
    });
  }
  update();
  document.addEventListener('mira:catalog-updated', update);
  setInterval(update, 60000);
})();
