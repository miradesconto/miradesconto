'use strict';
(() => {
    const hero = document.querySelector('.hero');
    if (!hero || !Array.isArray(products)) return;

    const activeProducts = products.filter(p =>
        p && p.available !== false && p.name && Number(p.price) > 0 && safeUrl(p.imageUrl) && safeUrl(p.affiliateUrl)
    );

    const featured = activeProducts[0] || null;
    const categoryCounts = activeProducts.reduce((acc, product) => {
        const name = String(product.category || '').trim();
        if (name) acc[name] = (acc[name] || 0) + 1;
        return acc;
    }, {});
    const topCategories = Object.entries(categoryCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 3);

    const money = value => new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(Number(value) || 0);

    hero.setAttribute('aria-label', 'Destaques do MiraDesconto');

    const shell = element('div', 'hero-static');
    const copy = element('div', 'hero-static-copy');
    copy.append(
        element('div', 'hero-static-eyebrow', 'OFERTAS + CONTEÚDO PARA DECIDIR MELHOR'),
        element('h1', '', 'Seu atalho para comprar melhor.'),
        element('p', '', 'Produtos do catálogo, guias diretos e comparações sem enrolação. Você encontra o que interessa e decide com mais clareza.')
    );

    const actions = element('div', 'hero-static-actions');
    const offers = element('a', 'hero-primary', 'Explorar ofertas →');
    offers.href = '#ofertas';
    const guides = element('a', 'hero-secondary', 'Ver guias e reviews');
    guides.href = 'blog/';
    actions.append(offers, guides);

    const note = element('p', 'hero-static-note', `${activeProducts.length} produtos no catálogo. Confira disponibilidade na loja.`);
    copy.append(actions, note);

    const dashboard = element('div', 'hero-dashboard');

    if (featured) {
        const deal = element('article', 'hero-deal');
        const visual = element('div', 'hero-deal-visual');
        const img = element('img');
        img.src = featured.imageUrl;
        img.alt = featured.name;
        img.width = 360;
        img.height = 270;
        img.decoding = 'async';
        img.addEventListener('error', () => visual.classList.add('image-error'), {once: true});
        visual.append(img);

        const info = element('div', 'hero-deal-info');
        info.append(element('span', 'hero-card-kicker', 'NO CATÁLOGO'));
        const title = element('h2', '', featured.name);
        const price = element('strong', 'hero-deal-price');
        const refreshPrice = () => { price.textContent = MiraQuality.usablePrice(featured) ? money(featured.price) : 'Ver preço na loja'; };
        refreshPrice();
        setInterval(refreshPrice, 60000);
        const link = element('a', 'hero-deal-link', 'Ver oferta →');
        link.href = featured.affiliateUrl;
        link.target = '_blank';
        link.rel = 'sponsored nofollow noopener';
        info.append(title, price, link);
        deal.append(visual, info);
        dashboard.append(deal);
    }

    const side = element('div', 'hero-side');

    const guide = element('a', 'hero-info-card hero-guide-card');
    guide.href = 'blog/';
    guide.append(
        element('span', 'hero-card-kicker', 'GUIAS E REVIEWS'),
        element('h3', '', 'Pesquise antes de clicar em comprar'),
        element('p', '', 'Análises de produtos do catálogo, com informação útil e sem teste inventado.'),
        element('span', 'hero-card-link', 'Ver conteúdos →')
    );
    side.append(guide);

    const categories = element('div', 'hero-info-card hero-category-card');
    categories.append(
        element('span', 'hero-card-kicker', 'EXPLORE RÁPIDO'),
        element('h3', '', 'Vá direto ao que interessa')
    );
    const chips = element('div', 'hero-category-chips');
    topCategories.forEach(([name, count]) => {
        const button = element('button', 'hero-category-chip', `${name} · ${count}`);
        button.type = 'button';
        button.addEventListener('click', () => {
            const categoryButton = [...document.querySelectorAll('.category')]
                .find(item => item.dataset.category === name);
            if (categoryButton) categoryButton.click();
            document.querySelector('#ofertas')?.scrollIntoView({behavior: 'smooth', block: 'start'});
        });
        chips.append(button);
    });
    categories.append(chips);
    side.append(categories);

    dashboard.append(side);
    shell.append(copy, dashboard);
    hero.replaceChildren(shell);
})();
