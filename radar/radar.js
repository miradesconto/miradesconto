'use strict';
// Historical observations remain useful, but an old collection is not a current offer.
function radarPriceIsRecent(checkedAt, now = Date.now()) {
  if (typeof checkedAt !== 'string' || !/(Z|[+-]\d{2}:\d{2})$/.test(checkedAt)) return false;
  const age = now - Date.parse(checkedAt);
  return Number.isFinite(age) && age >= 0 && age <= 2 * 60 * 60 * 1000;
}
function refreshRadar(root = document, now = Date.now()) {
  root.querySelectorAll('.radar-card[data-checked-at]').forEach(card => {
    if (radarPriceIsRecent(card.dataset.checkedAt, now)) return;
    card.querySelector('.radar-badge').hidden = true;
    card.querySelector('.radar-price').textContent = 'Consultar preço na loja';
    card.querySelector('.radar-reason').textContent = 'Esta coleta expirou. Os valores abaixo são referências históricas, não uma oferta atual.';
    card.querySelector('.radar-primary').textContent = 'Conferir preço na loja ↗';
  });
}
if (typeof document !== 'undefined') {
  refreshRadar();
  setInterval(refreshRadar, 60000);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) refreshRadar(); });
}
if (typeof module !== 'undefined') module.exports = {radarPriceIsRecent, refreshRadar};
