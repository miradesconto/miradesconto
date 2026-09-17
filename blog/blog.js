'use strict';
// Progressive enhancement: all editorial content and catalog links are static.
document.querySelectorAll('.image-frame img').forEach(img => {
  const fallback = img.previousElementSibling;
  const fail = () => {img.classList.add('failed');img.setAttribute('aria-hidden','true');fallback.hidden = false;};
  const loaded = () => {img.classList.remove('failed');img.removeAttribute('aria-hidden');fallback.hidden = true;};
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
const status = document.getElementById('searchStatus');
const clear = document.getElementById('clearSearch');
const normalize = value => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
function search() {
  const words = normalize(input.value).split(/\s+/).filter(Boolean);
  let count = 0;
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
