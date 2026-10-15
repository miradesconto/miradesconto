'use strict';
const source = window.MIRA_DATA;
const requestedProduct = new URLSearchParams(window.location.search).get('produto');
// Retain the registered catalog; eligibility is checked every time we render.
// Catalogue data stays intact; the homepage only features recent, monetizable offers.
const MAX_HOME_OFFERS = 6; // Four curated cards + six grid cards = ten visible offers.
function directAffiliate(p) {
    const link = p?.affiliateUrl;
    if (typeof link !== 'string' || !/^https:\/\/meli\.la\/[A-Za-z0-9]+$/.test(link)) return false;
    if (['https://meli.la/1NguveN','https://meli.la/1pyBZm8'].includes(link)) return false;
    return p.affiliateLinkType !== 'list' && p.available !== false;
}
const products = (source?.products || []).filter(p => p.name && directAffiliate(p));
let selectedCategory = 'Seleção da hora';
let visibleCount = MAX_HOME_OFFERS;
let categoryBeforeSearch = null;
const $ = id => document.getElementById(id);
function safeUrl(value) {
    try { const u = new URL(value); return ['https:', 'http:'].includes(u.protocol) ? u.href : null; }
    catch { return null; }
}
function money(value) {
    return typeof value === 'number' && Number.isFinite(value) && value > 0
        ? value.toLocaleString('pt-BR', {style:'currency',currency:'BRL'}) : 'Ver preço na loja';
}
function currentPrice(p) { return MiraQuality.usablePrice(p) ? p.price : null; }
function recordedPrice(p) {
    const e = p.priceCheck;
    return e?.status === 'verified' && e.currency === 'BRL' && e.price === p.price
        && e.oldPrice === p.oldPrice && Number.isFinite(Date.parse(e.checkedAt))
        && typeof p.price === 'number' && Number.isFinite(p.price) && p.price > 0
        ? p.price : null;
}
function productDiscount(p) { return MiraQuality.usablePrice(p) ? calculateDiscount(p.oldPrice,p.price) : null; }
function calculateDiscount(oldPrice, price) {
    return oldPrice > price && price > 0 ? Math.round((1-price/oldPrice)*100) : null;
}
function normalize(value) { return String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase(); }
function selectCategory(button) {
    selectedCategory = button.dataset.category;
    document.querySelectorAll('.category').forEach(b => {
        b.classList.toggle('active', b === button);
        b.setAttribute('aria-pressed', String(b === button));
    });
    $('categorySelect').value = selectedCategory;
    $('sectionTitle').textContent = selectedCategory === 'Seleção da hora' ? 'Ofertas da hora' : selectedCategory === 'Destaques' ? 'Tecnologia em destaque' : selectedCategory === 'Todos' ? 'Todas as ofertas tech' : selectedCategory;
    $('selectionNotice').hidden = selectedCategory !== 'Seleção da hora';
    renderProducts();
}
function resetFilters() {
    $('searchInput').value = '';
    $('sortSelect').value = 'default';
    categoryBeforeSearch = 'Seleção da hora';
    updateSearch();
}
function element(tag, className, text) {
    const e = document.createElement(tag);
    if(className) e.className = className;
    if(text !== undefined) e.textContent = text;
    return e;
}
function isAffiliateList(p) {
    if (p.affiliateLinkType === 'product' || p.offerUrl) return false;
    return p.affiliateUrl === 'https://meli.la/1NguveN' || (source?.affiliateSources || []).includes(p.affiliateUrl) || (source?.products || []).filter(item => item.affiliateUrl === p.affiliateUrl).length > 1;
}
function makeCard(p) {
    const card = element('article','card');
    card.dataset.id = p.id;
    const visual = element('div','product-image');
    const placeholder = element('span','image-placeholder','Imagem não disponível');
    visual.append(placeholder);
    if(safeUrl(p.imageUrl)) {
        const img = element('img');
        img.alt = p.name;
        img.loading = 'lazy';
        img.decoding = 'async';
        img.width = 480; img.height = 360;
        placeholder.hidden = true;
        img.addEventListener('load', () => placeholder.hidden = true);
        img.addEventListener('error', () => {img.remove();placeholder.hidden = false;});
        img.src = p.imageUrl;
        visual.append(img);
    }
    const discount = productDiscount(p);
    if(discount) {
        const badge = element('span','discount',`-${discount}%`);
        badge.title = 'Desconto sobre o preço de referência informado pela loja; não comprova menor preço histórico.';
        visual.append(badge);
    }
    const content = element('div','card-content');
    content.append(element('div','category-label',p.category || 'Outros'),element('h3','',p.name));
    content.append(element('div','old-price',discount ? money(p.oldPrice) : ''));
    const recent = currentPrice(p) !== null;
    content.append(element('div','price',recent ? money(p.price) : 'Consultar preço'));
    if (recent) {
        const checked = new Date(p.priceCheck.checkedAt).toLocaleString('pt-BR', {timeZone:'America/Sao_Paulo'});
        content.append(element('p','store','Conferido em ' + checked + ' (Brasília)'));
    }
    content.append(element('div','store',recent ? p.store || 'Ver loja' : 'Preço e disponibilidade na loja'));
    const buttons = element('div','buttons');
    const a = element('a','offer-button',isAffiliateList(p) ? 'ABRIR LISTA NA LOJA' : 'CONFERIR PREÇO NA LOJA');
    a.dataset.itemId=p.id; a.dataset.itemName=p.name; a.dataset.itemCategory=p.category || '';
    a.dataset.destinationType=isAffiliateList(p) ? 'affiliate_list' : 'product';
    if (isAffiliateList(p)) content.append(element('p','store','O link abre uma lista de afiliados. Procure este modelo e confirme a configuração.'));
    a.href = safeUrl(p.offerUrl || p.affiliateUrl);
    a.target = '_blank';
    a.rel = p.affiliateUrl ? 'noopener noreferrer sponsored' : 'noopener noreferrer';
    const share = element('button','share-button','Compartilhar');
    share.type = 'button';
    const siteLink = new URL('./', window.location.href);
    siteLink.searchParams.set('produto', p.id);
    siteLink.hash = 'ofertas';
    share.addEventListener('click', () => shareProduct(p.name,siteLink.href));
    const history = element('button','share-button','Ver histórico de preço');
    history.type = 'button'; history.addEventListener('click', () => window.MiraHistory.open(p, history));
    const guideSlug = {'MLB4604524838':'asus-vivobook-go-15-ryzen-5','MLB3914161563':'asus-vivobook-go-15-ryzen-5','MLB4329495631':'samsung-essential-s3-24','MLB4196200841':'acer-nitro-v15-rtx-4060'}[p.id];
    if (guideSlug) { const guide=element('a','product-link','Ver análise de compra →'); guide.href='produtos/'+guideSlug+'/'; content.append(guide); }
    const extras = element('details','product-extras');
    extras.append(element('summary','','Mais opções'),history,share);
    buttons.append(a,extras);content.append(buttons);card.append(visual,content);
    return card;
}
// Rotate the eligible catalog hourly, interleaving categories for a varied first page.
// Deterministic within each hour: pagination and filter changes retain their order.
function rotateOffers(items, now = Date.now()) {
    const hour = Math.floor(now / 3600000);
    const groups = new Map();
    [...items].sort((a,b) => String(a.id).localeCompare(String(b.id))).forEach(p => {
        const category = p.category || 'Outros';
        if (!groups.has(category)) groups.set(category, []);
        groups.get(category).push(p);
    });
    const buckets = [...groups.keys()].sort().map(category => {
        const group = groups.get(category);
        const offset = hour % group.length;
        return group.slice(offset).concat(group.slice(0,offset));
    });
    if (!buckets.length) return [];
    const offset = hour % buckets.length;
    const ordered = buckets.slice(offset).concat(buckets.slice(0,offset));
    const result = [];
    for (let row = 0; row < Math.max(...ordered.map(group => group.length)); row++) {
        ordered.forEach(group => { if (group[row]) result.push(group[row]); });
    }
    return result;
}
function filteredProducts() {
    const query = normalize($('searchInput').value.trim());
    const featuredIds = window.MiraShowcaseIds || [];
    const filtered = products.filter(p => MiraQuality.usablePrice(p) && directAffiliate(p)
        && (selectedCategory !== 'Seleção da hora' || !featuredIds.includes(p.id))
        && (selectedCategory === 'Todos' || selectedCategory === 'Seleção da hora' || (selectedCategory === 'Destaques' ? p.featured === true : p.category === selectedCategory))
        && [p.id,p.name,p.store,p.category].some(v=>normalize(v).includes(query)));
    switch($('sortSelect').value) {
        case 'discount': filtered.sort((a,b)=>(productDiscount(b)||0)-(productDiscount(a)||0));break;
        case 'lowPrice': filtered.sort((a,b)=>(currentPrice(a) ?? Infinity)-(currentPrice(b) ?? Infinity));break;
        case 'highPrice': filtered.sort((a,b)=>(currentPrice(b) ?? -Infinity)-(currentPrice(a) ?? -Infinity));break;
        default: if (selectedCategory === 'Seleção da hora') {
            // Choose strong verified discounts before rotating categories and items.
            const ranked = filtered.sort((a,b) => (Number(b.featured === true) - Number(a.featured === true))
                || ((productDiscount(b) || 0) - (productDiscount(a) || 0))
                || String(a.id).localeCompare(String(b.id)));
            return rotateOffers(ranked.slice(0,30));
        }
    }
    return filtered;
}
function renderProducts(keepCount = false) {
    visibleCount = MAX_HOME_OFFERS;
    const filtered = filteredProducts();
    const chosen = filtered.slice(0,visibleCount);
    $('productList').replaceChildren(...chosen.map(makeCard));
    if (selectedCategory === 'Seleção da hora') {
        window.MiraHomepageSelection = [...(window.MiraShowcaseIds || []), ...chosen.map(p=>p.id)];
    }
    document.body.classList.toggle('focused-catalog', selectedCategory !== 'Seleção da hora');
    // Only focus one curated selection, not 110 unverified/expired listing records.
    $('dataNotice').textContent = 'Valores exibidos foram conferidos há no máximo 2 horas. Quando o preço expira, consulte na loja. Pix, cupons e frete podem alterar o total.';
    $('resultCount').textContent = `${chosen.length} ${chosen.length===1?'oferta com preço conferido':'ofertas com preços conferidos'}`;
    if (document.body.classList.contains('search-active')) {
        $('searchMessage').textContent = `Busca em todo o catálogo por “${$('searchInput').value.trim()}”`;
    }
    $('emptyState').style.display = chosen.length ? 'none':'block';
    $('emptyState').querySelector('h3').textContent = 'Nenhuma oferta com preço recente nesta seleção.';
    $('emptyState').querySelector('p').textContent = 'A coleta automática pode estar atrasada. Confira novamente depois da próxima atualização.';
    $('loadMore').hidden = true;
    $('loadMore').textContent = '';
}
async function shareProduct(name,link) {
    const text = `${name} — encontrei no MiraDesconto`;
    if(navigator.share) {
        try { await navigator.share({title:name,text,url:link});return; }
        catch(e) { if(e.name === 'AbortError') return; }
    }
    try { await navigator.clipboard.writeText(`${text}\n${link}`);$('shareStatus').textContent = 'Link copiado!'; }
    catch { window.prompt('Copie o link da oferta:',link); }
}
const categoryContainer = document.querySelector('.categories-container');
const techCategories = ['PC e hardware','Notebooks','Celulares','Setup','Gaming','Áudio','Smart Home','TVs e projetores','Impressoras'];
const availableCategories = techCategories;
const categories = ['Seleção da hora','Todos',...availableCategories];
categoryContainer.replaceChildren();
const mobileCategory = element('div','category-mobile');
const categoryLabel = element('label','','Categoria');
categoryLabel.htmlFor = 'categorySelect';
const categorySelect = element('select');categorySelect.id = 'categorySelect';
mobileCategory.append(categoryLabel,categorySelect);
[...new Set(categories)].forEach(cat=>{
    const label = cat === 'Todos' ? 'Todas as ofertas' : cat;
    const b = element('button','category',label);
    b.type = 'button';b.dataset.category = cat;
    b.classList.toggle('active',cat===selectedCategory);b.setAttribute('aria-pressed',String(cat===selectedCategory));
    b.addEventListener('click',()=>selectCategory(b));categoryContainer.append(b);
    const option=element('option','',label);option.value=cat;categorySelect.append(option);
});
categoryContainer.append(mobileCategory);
categorySelect.addEventListener('change',()=>selectCategory([...categoryContainer.querySelectorAll('.category')].find(b=>b.dataset.category===categorySelect.value)));
function updateSearch() {
    const query = $('searchInput').value.trim();
    const wasSearching = document.body.classList.contains('search-active');
    if (query) {
        if (categoryBeforeSearch === null) categoryBeforeSearch = selectedCategory;
        document.body.classList.add('search-active');
        $('searchContext').hidden = false;
        selectCategory([...categoryContainer.querySelectorAll('.category')].find(b=>b.dataset.category==='Todos'));
        $('sectionTitle').textContent = `Resultados para “${query}”`;
        if (!wasSearching) requestAnimationFrame(()=>$('ofertas').scrollIntoView({behavior:'smooth',block:'start'}));
    } else {
        document.body.classList.remove('search-active');
        $('searchContext').hidden = true;
        const restore = categoryBeforeSearch || selectedCategory;
        categoryBeforeSearch = null;
        selectCategory([...categoryContainer.querySelectorAll('.category')].find(b=>b.dataset.category===restore));
        if (wasSearching) window.scrollTo({top:0,behavior:'smooth'});
    }
}
$('searchInput').addEventListener('input',updateSearch);
$('clearSearch').addEventListener('click',()=>{$('searchInput').value='';updateSearch();});
$('sortSelect').addEventListener('change',renderProducts);
document.querySelector('.logo').addEventListener('click',resetFilters);
// No infinite browsing on the homepage: a small, high-confidence selection.
$('selectionNotice').textContent = 'Seleção de até 10 ofertas com links individuais e preços conferidos recentemente.';
$('dataNotice').textContent = source
    ? 'Preços conferidos há no máximo 2 horas. Pix e cupons podem alterar o valor; confirme as condições na loja.'
    : 'Não foi possível carregar as ofertas. Tente recarregar a página em instantes.';
// Links editoriais podem consultar um registro antigo identificado, com aviso explícito.
if (requestedProduct) {
    $('searchInput').value = products.find(p => p.id === requestedProduct)?.name || requestedProduct;
    selectedCategory = 'Todos';
}
selectCategory([...categoryContainer.querySelectorAll('.category')].find(b=>b.dataset.category===selectedCategory));
if ($('searchInput').value.trim()) updateSearch();

// Recheck expiry while the visitor keeps the page open.
setInterval(() => renderProducts(true), 60000);
document.addEventListener('mira:showcase-updated',()=>renderProducts(true));

// Load the same published catalog without executing downloaded JavaScript.
// Each shard is checked atomically; a failed refresh preserves the previous data.
let catalogRefreshing = false;
async function refreshCatalog() {
    if (document.hidden || catalogRefreshing) return;
    catalogRefreshing = true;
    try {
        const response = await fetch('produtos.js', {cache:'no-store'});
        if (!response.ok) return;
        const text = await response.text();
        // Parse the generated JSON assignment as data; never execute downloaded code.
        const match = text.match(/(?:^|\n)window\.MIRA_DATA\s*=\s*(\{[\s\S]*\})\s*;?\s*$/);
        if (!match) return;
        const next = JSON.parse(match[1]).products;
        if (!Array.isArray(next)) return;
        if (!next.length || new Set(next.map(p => p.id)).size !== next.length) return;
        if (next.some(p => !p || typeof p.id !== 'string' || !p.id || !p.name || !safeUrl(p.affiliateUrl))) return;
        products.splice(0, products.length, ...next.filter(p => directAffiliate(p)));
        if (!products.length) return;
        if (source) source.products = next;
        document.dispatchEvent(new CustomEvent('mira:catalog-updated'));
        renderProducts(true);
    } catch { /* Retain existing data; the freshness guard still expires prices. */ }
    finally { catalogRefreshing = false; }
}
refreshCatalog();
setInterval(refreshCatalog, 60000);
document.addEventListener('visibilitychange', () => { if (!document.hidden) refreshCatalog(); });
