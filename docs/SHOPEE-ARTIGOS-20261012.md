# Shopee — dez artigos isolados (fase 1)

- Origem: arquivo de exportação em massa da Shopee de 12/10/2026, 59 itens originais. Este CSV derivado contém **somente os dez anúncios selecionados** e seus links exatos, sem regenerar links de comissão.
- Arquivo: `_data/shopee_ofertas.csv`. É lido diretamente pelo Jekyll no include `_includes/link-shopee.html`; não entra em `dados/catalogo.json`, `produtos.js`, `catalogo/produtos-*.json` nem nas coletas automáticas do Mercado Livre.
- Artigos: `_artigos/*-shopee.md`. Estão em `status: "rascunho"`; **não ficam publicados após o merge** sem mudança explícita para `publicado`. Atenção: o texto continua visível no GitHub público.
- Preço: referência do CSV, não valor atual. Estoque não confirmado; comissão não garantida. Links 1 a 4 foram abertos manualmente pelo responsável; ele informou que os links estão em ordem. Os itens 5 a 10 ainda não têm comprovação individual de redirecionamento nesta auditoria.
- Imagem: o CSV original não incluía `image_url`. Foram coletadas as imagens principais dos dez anúncios Shopee com IDs exatos; o CSV editorial passou a incluir essas URLs. Conferir o carregamento real e variações antes de publicar. Não usar fotos do Mercado Livre.
- Para publicar depois da revisão: preencher data real, confirmar link e foto (se houver), mudar status, rodar `node blog/verify.cjs`, `python -m unittest discover -s tests -q` e revisar a página no navegador.
- Não existe ligação de oferta Shopee ao Radar de preços do ML. O Radar continua referenciando somente seus anúncios com evidência.

## Imagens da Shopee implementadas

- `_data/shopee_ofertas.csv` contém as dez URLs no CDN Shopee.
- `_data/produtos_unificados.json` usa `image_url`, `image_source` e `image_source_type`, sem dependência do CDN/API do Mercado Livre.
- O frontmatter dos artigos registra `custom_image` e `image_source`. `_includes/foto-shopee.html` mostra a foto e avisa sobre variações.
- O hub `blog/index.html` usa `entry.custom_image` quando não há produto no catálogo ML; o layout do artigo usa a foto própria para `og:image`.
- O layout/CSS original foi preservado; nenhum post foi publicado. Não basta CI aprovado: verificar imagens remotas em smartphone e desktop.
