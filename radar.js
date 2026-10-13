'use strict';
const MiraRadar = (() => {
  const maxAge = 2 * 3600000;
  function fresh(item, now = Date.now()) {
    const time = typeof item?.checkedAt === 'string' && /(Z|[+-]\d{2}:\d{2})$/.test(item.checkedAt) ? Date.parse(item.checkedAt) : NaN;
    return Number.isFinite(time) && now >= time && now - time <= maxAge;
  }
  function eligible(item, now = Date.now()) {
    return fresh(item, now) && item.actionable === true && item.strength >= 2
      && item.observations >= 6 && item.spanDays >= 7
      && ['Menor observado','Excelente preço','Bom preço'].includes(item.label)
      && Number.isFinite(item.currentPrice) && item.currentPrice > 0
      && /^https:\/\/meli\.la\/[a-zA-Z0-9]+$/.test(item.affiliateUrl)
      && /^https:\/\//.test(item.imageUrl);
  }
  function choose(items, now = Date.now(), category = '') {
    const hour = Math.floor(now / 3600000);
    const groups = new Map();
    for (const item of items) if (eligible(item, now) && (!category || category === item.category)) {
      if (!groups.has(item.category)) groups.set(item.category, []);
      groups.get(item.category).push(item);
    }
    let buckets = [...groups.keys()].sort().map(key => {
      const group = groups.get(key).sort((a,b) => b.strength - a.strength || a.deltaAveragePct - b.deltaAveragePct || a.id.localeCompare(b.id));
      const offset = hour % group.length;
      return group.slice(offset).concat(group.slice(0,offset));
    });
    if (!buckets.length) return [];
    const offset = hour % buckets.length;
    buckets = buckets.slice(offset).concat(buckets.slice(0,offset));
    const result = [];
    // Category filtering shows up to 12 results; the mixed view allows 3 per category.
    for (let row = 0; row < (category ? 12 : 3); row++) {
      for (const group of buckets) if (group[row]) result.push(group[row]);
      if (result.length >= 12) break;
    }
    return result.slice(0,12);
  }
  return {fresh, eligible, choose};
})();
if (typeof module !== 'undefined') module.exports = MiraRadar;
if (typeof window !== 'undefined') window.MiraRadar = MiraRadar;
if (typeof document !== 'undefined') (() => {
  const grid = document.getElementById('radarGrid');
  if (!grid) return;
  let data;
  try { data = JSON.parse(document.getElementById('radar-data').textContent); } catch { return; }
  const select = document.getElementById('radarCategory');
  const status = document.getElementById('radarStatus');
  let signature = '';
  let refreshing = false;
  const node = (tag, className, text) => {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text !== undefined) el.textContent = text;
    return el;
  };
  const money = value => value.toLocaleString('pt-BR', {style:'currency',currency:'BRL'});
  function card(item) {
    const article = node('article','radar-card'); article.dataset.productId = item.id;
    const imageBox = node('div','radar-card-image');
    const img = node('img'); img.src = item.imageUrl; img.alt = item.name;
    img.width = 420; img.height = 300; img.loading = 'lazy';
    img.addEventListener('error', () => imageBox.replaceChildren(node('span','image-placeholder','Imagem indisponível')), {once:true});
    imageBox.append(img);
    const body = node('div','radar-card-body');
    const top = node('div','radar-card-top');
    top.append(node('span','radar-badge badge-good',item.label),node('span','radar-category',item.category));
    const detail = node('details','radar-detail');
    detail.append(node('summary','','Ver histórico e comparação'));
    const facts = node('div','radar-facts');
    for (const [label,value] of [['Média observada',money(item.averagePrice)],['Menor observado',money(item.minimumPrice)],['Base da análise',item.periodText]]) {
      const row = node('div'); row.append(node('span','',label),node('strong','',value)); facts.append(row);
    }
    detail.append(facts,node('p','radar-evidence',`${item.observations} observações verificadas no mesmo anúncio e variação.`));
    const actions = node('div','radar-actions');
    const buy = node('a','radar-primary','Conferir oferta ↗');
    buy.href = item.affiliateUrl; buy.target = '_blank'; buy.rel = 'sponsored nofollow noopener noreferrer';
    buy.dataset.itemId = item.id; buy.dataset.itemName = item.name; buy.dataset.linkLocation = 'radar';
    const catalog = node('a','radar-secondary','Ver no catálogo'); catalog.href = '../?produto=' + encodeURIComponent(item.id) + '#ofertas';
    actions.append(buy,catalog);
    body.append(top,node('h3','',item.name),node('div','radar-price',money(item.currentPrice)),node('p','radar-reason',item.reason),detail,actions);
    article.append(imageBox,body); return article;
  }
  function render() {
    const now = Date.now(), all = Object.values(data.byId || {});
    const qualified = all.filter(item => MiraRadar.eligible(item, now));
    const categories = [...new Set(qualified.map(item => item.category))].sort();
    const selected = select.value;
    const options = [node('option','','Todas'),...categories.map(category => {const option = node('option','',category); option.value = category; return option;})];
    options[0].value = '';
    select.replaceChildren(...options); select.value = categories.includes(selected) ? selected : '';
    const items = MiraRadar.choose(all, now, select.value);
    const nextSignature = JSON.stringify(items);
    if (signature !== nextSignature) {
      grid.replaceChildren(...items.map(card)); signature = nextSignature;
    }
    document.getElementById('radarEmpty').hidden = items.length > 0;
    document.getElementById('radarFeaturedCount').textContent = items.length;
    document.getElementById('radarEligibleCount').textContent = all.filter(item => MiraRadar.fresh(item, now)).length;
    status.textContent = items.length ? 'Seleção da hora · apenas preços conferidos nas últimas 2 horas.' : 'Nenhuma oportunidade com preço recente e histórico suficiente. Explore as ofertas ou os guias.';
    const generated = new Date(data.generatedAt);
    if (Number.isFinite(generated.getTime())) document.getElementById('radarUpdatedAt').textContent = generated.toLocaleString('pt-BR', {timeZone:'America/Sao_Paulo'}) + ' (Brasília)';
  }
  async function refresh() {
    if (document.hidden || refreshing) return;
    refreshing = true;
    try {
      const response = await fetch('../radar/feed.json', {cache:'no-store'});
      if (!response.ok) throw new Error('Radar unavailable');
      const next = await response.json();
      if (!next.byId || !Number.isFinite(Date.parse(next.generatedAt))) throw new Error('Invalid radar');
      if (Date.parse(next.generatedAt) >= Date.parse(data.generatedAt)) data = next;
    } catch { /* Existing evidence still expires against the actual clock. */ }
    finally { refreshing = false; render(); }
  }
  select.addEventListener('change',render);
  render(); refresh();
  setInterval(render,60000); setInterval(refresh,5 * 60000);
  document.addEventListener('visibilitychange', () => {if (!document.hidden) refresh();});
})();
