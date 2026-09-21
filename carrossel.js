'use strict';
(() => {
    const hero = document.querySelector('.hero');
    if (!hero || !Array.isArray(products)) return;
    const eligible = products.filter(p => p && p.available !== false && p.name && safeUrl(p.imageUrl) && safeUrl(p.affiliateUrl));
    const counts = new Map();
    eligible.forEach(p => { if (p.category) counts.set(p.category, (counts.get(p.category) || 0) + 1); });
    const categories = [...counts].sort((a,b) => b[1]-a[1]).slice(0,4);
    const chosen = [];
    for (const p of eligible) {
        if (!chosen.some(item => item.category === p.category)) chosen.push(p);
        if (chosen.length === 2) break;
    }
    for (const p of eligible) {
        if (chosen.length === 2) break;
        if (!chosen.includes(p)) chosen.push(p);
    }
    const select = name => {
        const button = [...document.querySelectorAll('.category')].find(b => b.dataset.category === name);
        if (button) { document.getElementById('searchInput').value = ''; button.click(); }
    };
    const shell = element('div','hero-static');
    const main = element('div','hero-main');
    const copy = element('div','hero-static-copy');
    const heading = element('h1');
    heading.append(document.createTextNode('Comprar melhor começa com '), element('span','','uma boa escolha.'));
    copy.append(element('p','hero-static-eyebrow','MIRADESCONTO · ESCOLHAS DO DIA A DIA'), heading,
        element('p','hero-intro','Explore produtos, compare opções e tire suas dúvidas antes de comprar. Tudo em um só lugar.'));
    const actions = element('div','hero-static-actions');
    const offers = element('a','hero-primary','Explorar produtos'); offers.href = '#ofertas';
    offers.addEventListener('click', () => select('Todos'));
    const guides = element('a','hero-secondary','Ler guias de compra ↗'); guides.href = 'blog/';
    actions.append(offers,guides); copy.append(actions);
    copy.append(element('p','hero-static-note', eligible.length + ' produtos para explorar · Confira preço e disponibilidade na loja.'));
    const showcase = element('div','hero-showcase');
    const showcaseHead = element('div','hero-showcase-head');
    showcaseHead.append(element('span','hero-card-kicker','ENCONTRE NO CATÁLOGO'),element('span','hero-selection-note','Para começar sua busca'));
    const grid = element('div','hero-picks');
    const refreshers = [];
    chosen.forEach(p => {
        const card = element('a','hero-deal');
        card.href = safeUrl(p.affiliateUrl); card.target = '_blank'; card.rel = 'sponsored nofollow noopener noreferrer';
        card.setAttribute('aria-label', p.name + ': conferir na loja, abre em nova aba');
        const visual = element('div','hero-deal-visual');
        const img = element('img'); img.src = safeUrl(p.imageUrl); img.alt = ''; img.width = 220; img.height = 190; img.decoding = 'async';
        img.addEventListener('error', () => { img.remove(); visual.append(element('span','hero-image-fallback','Imagem indisponível')); },{once:true});
        visual.append(img);
        const info = element('div','hero-deal-info');
        const title = element('h2','',p.name); title.title = p.name;
        const price = element('strong','hero-deal-price');
        const status = element('span','hero-price-note');
        const refresh = () => {
            const verified = MiraQuality.usablePrice(p);
            price.textContent = verified ? money(p.price) : 'Ver preço na loja';
            status.textContent = verified ? 'Preço verificado nas últimas 24 h' : 'Consulte as condições atuais';
        };
        refresh(); refreshers.push(refresh);
        info.append(element('span','hero-product-category',p.category || 'No catálogo'),title,price,status,element('span','hero-deal-link','Conferir na loja ↗'));
        card.append(visual,info); grid.append(card);
    });
    if (!chosen.length) grid.append(element('p','hero-no-products','Explore nossos guias enquanto o catálogo é atualizado.'));
    showcase.append(showcaseHead,grid); main.append(copy,showcase);
    const bottom = element('div','hero-bottom');
    const quick = element('nav','hero-quick'); quick.setAttribute('aria-label','Explorar categorias do catálogo');
    quick.append(element('span','hero-quick-label','O que você procura?'));
    const chips = element('div','hero-category-chips');
    categories.forEach(([name,count]) => {
        const link = element('a','hero-category-chip'); link.href = '#ofertas';
        link.append(element('span','',name),element('span','hero-category-count',String(count)));
        link.addEventListener('click', () => select(name)); chips.append(link);
    });
    quick.append(chips);
    const guide = element('a','hero-guide-card'); guide.href = 'blog/';
    guide.append(element('span','hero-guide-icon','↗'),element('span','','Na dúvida? Comece pelos guias.'));
    bottom.append(quick,guide); shell.append(main,bottom);
    hero.setAttribute('aria-label','Explore produtos e guias do MiraDesconto'); hero.replaceChildren(shell);
    if (refreshers.length) setInterval(() => refreshers.forEach(refresh => refresh()),60000);
})();
