'use strict';
const source = window.MIRA_DATA;
const products = (source?.products || []).filter(p => p.name && safeUrl(p.affiliateUrl));
let selectedCategory = 'Destaques';
let visibleCount = 24;
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
    $('sectionTitle').textContent = selectedCategory === 'Destaques' ? 'Produtos em destaque' : selectedCategory === 'Todos' ? 'Todos os produtos' : selectedCategory;
    $('selectionNotice').hidden = selectedCategory !== 'Destaques';
    renderProducts();
}
function resetFilters() {
    $('searchInput').value = '';
    $('sortSelect').value = 'default';
    selectCategory(document.querySelector('.category'));
}
function element(tag, className, text) {
    const e = document.createElement(tag);
    if(className) e.className = className;
    if(text !== undefined) e.textContent = text;
    return e;
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
        img.addEventListener('load', () => placeholder.hidden = true);
        img.addEventListener('error', () => {img.remove();placeholder.hidden = false;});
        img.src = p.imageUrl;
        visual.append(img);
    }
    const discount = productDiscount(p);
    if(discount) visual.append(element('span','discount',`-${discount}%`));
    const content = element('div','card-content');
    content.append(element('div','category-label',p.category || 'Outros'),element('h3','',p.name));
    content.append(element('div','old-price',discount ? money(p.oldPrice) : ''));
    const recent = currentPrice(p) !== null;
    content.append(element('div','price',money(recent ? p.price : recordedPrice(p))));
    if (!recent && recordedPrice(p) !== null) {
        const date = new Date(p.priceCheck.checkedAt).toLocaleDateString('pt-BR',{timeZone:'America/Sao_Paulo'});
        content.append(element('div','store','Último preço registrado em '+date+' · confirme na loja'));
    } else content.append(element('div','store',p.store || 'Ver loja'));
    const buttons = element('div','buttons');
    const a = element('a','offer-button','VER NA LOJA');
    a.href = safeUrl(p.affiliateUrl);
    a.target = '_blank';
    a.rel = p.affiliateUrl ? 'noopener noreferrer sponsored' : 'noopener noreferrer';
    const share = element('button','share-button','Compartilhar');
    share.type = 'button';
    share.addEventListener('click', () => shareProduct(p.name,a.href));
    buttons.append(a,share);content.append(buttons);card.append(visual,content);
    return card;
}
function filteredProducts() {
    const query = normalize($('searchInput').value.trim());
    const filtered = products.filter(p => (selectedCategory === 'Todos' || (selectedCategory === 'Destaques' ? p.featured === true : p.category === selectedCategory))
        && [p.id,p.name,p.store,p.category].some(v=>normalize(v).includes(query)));
    switch($('sortSelect').value) {
        case 'discount': filtered.sort((a,b)=>(productDiscount(b)||0)-(productDiscount(a)||0));break;
        case 'lowPrice': filtered.sort((a,b)=>(currentPrice(a) ?? Infinity)-(currentPrice(b) ?? Infinity));break;
        case 'highPrice': filtered.sort((a,b)=>(currentPrice(b) ?? -Infinity)-(currentPrice(a) ?? -Infinity));break;
    }
    return filtered;
}
function renderProducts(keepCount = false) {
    if(keepCount !== true) visibleCount = 24;
    const filtered = filteredProducts();
    $('productList').replaceChildren(...filtered.slice(0,visibleCount).map(makeCard));
    $('resultCount').textContent = `${filtered.length} ${filtered.length===1?'oferta encontrada':'ofertas encontradas'}`;
    $('emptyState').style.display = filtered.length ? 'none':'block';
    $('loadMore').hidden = visibleCount >= filtered.length;
    $('loadMore').textContent = `Mostrar mais ofertas (${Math.min(visibleCount,filtered.length)} de ${filtered.length})`;
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
const availableCategories = [...new Set(products.map(p=>p.category || 'Outros'))].sort((a,b)=>a.localeCompare(b,'pt-BR'));
const categories = ['Destaques','Todos',...availableCategories];
categoryContainer.replaceChildren();
const mobileCategory = element('div','category-mobile');
const categoryLabel = element('label','','Categoria');
categoryLabel.htmlFor = 'categorySelect';
const categorySelect = element('select');categorySelect.id = 'categorySelect';
mobileCategory.append(categoryLabel,categorySelect);
[...new Set(categories)].forEach(cat=>{
    const count = products.filter(p=>cat==='Todos'||(cat==='Destaques'?p.featured===true:p.category===cat)).length;
    const label = `${cat} (${count})`;
    const b = element('button','category',label);
    b.type = 'button';b.dataset.category = cat;
    b.classList.toggle('active',cat===selectedCategory);b.setAttribute('aria-pressed',String(cat===selectedCategory));
    b.addEventListener('click',()=>selectCategory(b));categoryContainer.append(b);
    const option=element('option','',label);option.value=cat;categorySelect.append(option);
});
categoryContainer.append(mobileCategory);
categorySelect.addEventListener('change',()=>selectCategory([...categoryContainer.querySelectorAll('.category')].find(b=>b.dataset.category===categorySelect.value)));
// Header search is global, so non-featured products remain discoverable.
$('searchInput').addEventListener('input',()=>selectCategory([...categoryContainer.querySelectorAll('.category')].find(b=>b.dataset.category==='Todos')));
$('sortSelect').addEventListener('change',renderProducts);
document.querySelector('.logo').addEventListener('click',resetFilters);
$('loadMore').addEventListener('click',()=>{visibleCount+=24;renderProducts(true);});
$('dataNotice').textContent = source
    ? 'Valores antigos são identificados pela data da última coleta. Confirme preço e disponibilidade na loja.'
    : 'Não foi possível carregar as ofertas. Verifique se produtos.js está na mesma pasta do site.';
// Editorial links open the matching catalog record, including items beyond page one.
const requestedProduct = new URLSearchParams(window.location.search).get('produto');
if (requestedProduct) {
    $('searchInput').value = products.find(p => p.id === requestedProduct)?.name || requestedProduct;
    selectedCategory = 'Todos';
}
selectCategory([...categoryContainer.querySelectorAll('.category')].find(b=>b.dataset.category===selectedCategory));

// Recheck expiry while the visitor keeps the page open.
setInterval(() => renderProducts(true), 60000);
