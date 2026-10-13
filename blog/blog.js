'use strict';
// Progressive enhancement: all editorial content and catalog links are static.
document.querySelectorAll('.image-frame img, .editorial-card-media img, .product-media img, .radar-card-image img, .buy-card > img').forEach(img => {
  let fallback = img.parentElement.querySelector('.image-fallback, .media-fallback');
  // Keep the registered source. A failed image never justifies substituting another product.
  if (!fallback) {
    fallback = document.createElement('span');
    fallback.className = 'media-fallback';
    fallback.textContent = 'Imagem indisponível';
    img.after(fallback);
  }
  fallback.hidden = true;
  const fail = () => {img.hidden = true;img.setAttribute('aria-hidden','true');fallback.hidden = false;};
  const loaded = () => {img.hidden = false;img.removeAttribute('aria-hidden');fallback.hidden = true;};
  img.addEventListener('error', fail);
  img.addEventListener('load', loaded);
  if (img.complete) {if (img.naturalWidth) loaded(); else fail();}
});
(() => {
const input = document.getElementById('articleSearch');
if (!input) return;
const form = document.querySelector('.search-form');
const sections = [...document.querySelectorAll('.topic')];
const cards = [...document.querySelectorAll('.topic .card')];
const feature = document.querySelector('.feature-section');
const featuredCard = feature?.querySelector('.featured');
const status = document.getElementById('searchStatus');
const clear = document.getElementById('clearSearch');
const normalize = value => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
function search() {
  const words = normalize(input.value).split(/\s+/).filter(Boolean);
  const featureMatch = featuredCard && words.every(word => normalize(featuredCard.dataset.search).includes(word));
  if (feature) feature.hidden = words.length > 0 && !featureMatch;
  let count = featureMatch ? 1 : 0;
  cards.forEach(card => {
    card.hidden = !words.every(word => normalize(card.dataset.search).includes(word));
    if (!card.hidden) count++;
  });
  sections.forEach(section => {section.hidden = ![...section.querySelectorAll('.card')].some(card => !card.hidden);});
  clear.hidden = !input.value;
  status.hidden = false;
  status.textContent = `${count} ${count === 1 ? 'pauta encontrada' : 'pautas encontradas'}.`;
  document.getElementById('emptyState').hidden = count > 0;
}
function reset() {input.value = '';search();}
form.hidden = false;
form.addEventListener('submit', event => {event.preventDefault();search();});
input.addEventListener('input', search);
clear.addEventListener('click', () => {reset();input.focus();});
document.getElementById('resetSearch').addEventListener('click', () => {reset();input.focus();});
document.querySelectorAll('.toolbar nav a').forEach(link => link.addEventListener('click', reset));

})();
