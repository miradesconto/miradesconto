// Run from any directory: node blog/build.cjs. Static output works without JavaScript.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const context = {window: {}};
vm.runInNewContext(fs.readFileSync(path.join(root, 'produtos.js'), 'utf8'), context);
const source = context.window.MIRA_DATA;
const chunks = fs.readdirSync(path.join(root, 'catalogo')).filter(f => f.endsWith('.json')).flatMap(f => JSON.parse(fs.readFileSync(path.join(root, 'catalogo', f), 'utf8')));
const entries = JSON.parse(fs.readFileSync(path.join(__dirname, 'pautas.json'), 'utf8'));
const labels = {reviews: 'Reviews', comparativos: 'Comparativos', guias: 'Guias de compra'};
const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
const validURL = s => {try {return new URL(s).protocol === 'https:';} catch {return false;}};
const getProduct = id => {
  const p = source.products.find(p => p.id === id);
  const mirror = chunks.find(p => p.id === id);
  if (!p || !mirror || !validURL(p.affiliateUrl) || !validURL(p.imageUrl) || p.imageUrl !== mirror.imageUrl || p.affiliateUrl !== mirror.affiliateUrl || p.name !== mirror.name) throw new Error(`Produto ausente, indisponível ou divergente: ${id}`);
  return p;
};
const productLink = p => `<a class="product-link" href="../?produto=${encodeURIComponent(p.id)}#ofertas">Ver no catálogo <span class="sr-only">${esc(p.name)}</span><span aria-hidden="true">↗</span></a>`;
const visual = (products, feature = false) => `<div class="visual ${products.length > 1 ? 'pair' : ''}">${products.map(p => `<div class="image-frame"><span class="image-fallback">${esc(p.name)}<small>Imagem indisponível</small></span><img src="${esc(p.imageUrl)}" alt="${esc(p.name)}" width="480" height="360" ${feature ? 'fetchpriority="high"' : 'loading="lazy"'} decoding="async"></div>`).join('')}</div>`;
const card = (entry, feature = false) => {
 const products = entry.ids.map(getProduct);
 return `<article class="${feature ? 'featured' : 'card'}" data-search="${esc([entry.title,entry.summary,labels[entry.type],...products.map(p=>p.name)].join(' '))}">
 ${visual(products, feature)}<div class="card-copy"><div class="eyebrow">${labels[entry.type]} · Pauta editorial</div><h${feature ? '3' : '3'}>${esc(entry.title)}</h3><p>${esc(entry.summary)}</p><div class="product-links">${products.map(p => `<div><p class="product-name">${esc(p.name)}</p>${productLink(p)}</div>`).join('')}</div></div></article>`;
};
const featured = entries.find(e => e.featured);
if (!featured || entries.filter(e=>e.featured).length !== 1) throw new Error('Defina um único destaque.');
const schema = {'@context':'https://schema.org','@graph':[
 {'@type':'Organization','@id':'https://miradesconto.github.io/miradesconto/#organization','name':'MiraDesconto','url':'https://miradesconto.github.io/miradesconto/'},
 {'@type':'CollectionPage','@id':'https://miradesconto.github.io/miradesconto/blog/#page','url':'https://miradesconto.github.io/miradesconto/blog/','name':'Blog MiraDesconto — Guias, Reviews e Comparativos','description':'Pautas editoriais ligadas a produtos reais do catálogo. Ainda sem reviews, comparativos ou guias pesquisados publicados.','inLanguage':'pt-BR','publisher':{'@id':'https://miradesconto.github.io/miradesconto/#organization'}},
 {'@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':1,'name':'MiraDesconto','item':'https://miradesconto.github.io/miradesconto/'},{'@type':'ListItem','position':2,'name':'Blog','item':'https://miradesconto.github.io/miradesconto/blog/'}]}
]};
const html = `<!doctype html>
<html lang="pt-BR"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Blog MiraDesconto — Guias, Reviews e Comparativos</title>
<meta name="description" content="Explore pautas de reviews, comparativos e guias ligadas ao catálogo real do MiraDesconto. Conheça os produtos e nossa proposta editorial, sem análises inventadas.">
<meta name="theme-color" content="#ffffff"><link rel="icon" type="image/svg+xml" href="../favicon.svg">
<link rel="canonical" href="https://miradesconto.github.io/miradesconto/blog/">
<meta property="og:locale" content="pt_BR"><meta property="og:site_name" content="MiraDesconto"><meta property="og:type" content="website">
<meta property="og:title" content="MiraDesconto Editorial | Informação para escolher melhor">
<meta property="og:description" content="Produtos reais, perguntas relevantes e transparência. Explore as pautas do nosso blog e os itens do catálogo.">
<meta property="og:url" content="https://miradesconto.github.io/miradesconto/blog/">
<meta property="og:image" content="https://miradesconto.github.io/miradesconto/blog/social.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="MiraDesconto Editorial — Informação para escolher melhor">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="MiraDesconto Editorial"><meta name="twitter:description" content="Explore pautas editoriais ligadas ao catálogo real."><meta name="twitter:image" content="https://miradesconto.github.io/miradesconto/blog/social.png">
<link rel="stylesheet" href="blog.css"><script src="blog.js" defer></script>
<script type="application/ld+json">${JSON.stringify(schema)}</script>
</head><body>
<a class="skip" href="#conteudo">Pular para o conteúdo</a>
<header class="site-header"><div class="wrap header-inner"><a class="logo" href="../" aria-label="MiraDesconto, página inicial">Mira<span>Desconto</span></a><nav aria-label="Navegação principal"><a href="../">Ofertas</a><a href="./" aria-current="page">Guias e Reviews</a><a href="../sobre.html">Sobre</a></nav></div></header>
<main id="conteudo" class="wrap">
<section class="intro" aria-labelledby="intro-title"><p class="eyebrow">MiraDesconto Editorial</p><h1 id="intro-title">Informação para<br>escolher melhor.</h1><p class="lead">Uma boa compra começa com boas perguntas.<br class="desktop-break"> Explore os produtos que inspiram nossas próximas pautas.</p><a class="text-link" href="#pautas">Explorar pautas <span aria-hidden="true">↓</span></a></section>
<aside class="notice" aria-label="Status editorial"><span class="status-dot" aria-hidden="true"></span><p><strong>Nosso ponto de partida.</strong> Ainda não publicamos artigos pesquisados, reviews ou testes. As chamadas abaixo são pautas propostas, vinculadas a produtos reais do catálogo — não são recomendações de compra.</p></aside>
<section class="feature-section" aria-labelledby="feature-title"><div class="section-heading"><h2 id="feature-title">No radar editorial</h2><span>Uma pergunta antes da compra</span></div>${card(featured,true)}</section>
<section id="pautas" aria-labelledby="pautas-title"><div class="section-heading"><div><p class="eyebrow">Explore por assunto</p><h2 id="pautas-title">Pautas que começam no catálogo</h2></div></div>
<div class="toolbar"><nav aria-label="Seções do blog"><a href="#reviews">Reviews</a><a href="#comparativos">Comparativos</a><a href="#guias">Guias</a></nav><form role="search" class="search-form" hidden><label for="articleSearch">Buscar pautas</label><div class="search-control"><input id="articleSearch" type="search" placeholder="Produto ou assunto" autocomplete="off" aria-controls="sections"><button type="button" id="clearSearch" aria-label="Limpar busca" hidden>Limpar</button></div></form></div>
<p id="searchStatus" role="status" aria-live="polite" aria-atomic="true" hidden></p>
<div id="sections">${Object.entries(labels).map(([type,label]) => `<section id="${type}" class="topic" aria-labelledby="${type}-title"><div class="topic-heading"><h3 id="${type}-title">${label}</h3><span>${type === 'reviews' ? 'Perguntas sobre um produto' : type === 'comparativos' ? 'Opções para investigar lado a lado' : 'Critérios para orientar a escolha'}</span></div><div class="grid">${entries.filter(e => e.type === type).map(e=>card(e).replace(/<h3>/g,'<h4>').replace(/<\/h3>/g,'</h4>')).join('')}</div></section>`).join('')}</div>
<div id="emptyState" class="empty" hidden><h3>Nenhuma pauta encontrada</h3><p>Tente “cafeteira”, “Galaxy” ou “Mondial”, ou limpe a busca para ver todas.</p><button type="button" id="resetSearch">Ver todas as pautas</button></div>
<noscript><p class="notice">Todas as pautas estão disponíveis abaixo das categorias. Ative o JavaScript para usar a busca.</p></noscript>
</section>
<section class="method" aria-labelledby="method-title"><div><p class="eyebrow">Compromisso editorial</p><h2 id="method-title">Clareza antes<br>da recomendação.</h2><a href="../transparencia.html" class="text-link">Conheça nossa transparência →</a></div><div class="principles"><div><h3>Pesquisa com origem</h3><p>Para publicar uma análise, exigimos fontes identificadas, data de consulta e distinção entre informação do fabricante, da loja e experiência própria.</p></div><div><h3>Sem testes ou notas inventados</h3><p>Uma ficha de anúncio não comprova desempenho. Só apresentaremos testes próprios quando realmente realizados e com método explicado.</p></div><div><h3>Relação comercial à vista</h3><p>Links na vitrine podem gerar comissão em compras elegíveis, sem cobrança adicional por esse vínculo. Isso não substitui a apuração editorial.</p></div></div></section>
<section class="catalog-cta"><div><h2>Quer conhecer os produtos?</h2><p>Os registros usados nestas pautas foram coletados em ${esc(source.collectedAt)}. Confirme modelo, preço, frete e disponibilidade na loja.</p></div><a href="../">Explorar catálogo <span aria-hidden="true">↗</span></a></section>
</main>
<footer><div class="wrap footer-inner"><div><a class="logo" href="../">Mira<span>Desconto</span></a><p>Informação para escolher melhor.<br>© 2026 MiraDesconto.</p></div><nav aria-label="Informações institucionais"><a href="../sobre.html">Sobre</a><a href="../transparencia.html">Transparência</a><a href="../privacidade.html">Privacidade</a><a href="#conteudo">Voltar ao topo ↑</a></nav></div></footer>
</body></html>`;
fs.writeFileSync(path.join(__dirname, 'index.html'), html);
console.log(`Blog gerado: ${entries.length} pautas, ${new Set(entries.flatMap(e=>e.ids)).size} produtos validados em duas fontes.`);
