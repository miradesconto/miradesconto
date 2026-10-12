# Shopee — dez artigos isolados (fase 1)

- Origem: arquivo de exportação em massa da Shopee de 12/10/2026, 59 itens originais. Este CSV derivado contém **somente os dez anúncios selecionados** e seus links exatos, sem regenerar links de comissão.
- Arquivo: `_data/shopee_ofertas.csv`. É lido diretamente pelo Jekyll no include `_includes/link-shopee.html`; não entra em `dados/catalogo.json`, `produtos.js`, `catalogo/produtos-*.json` nem nas coletas automáticas do Mercado Livre.
- Artigos: `_artigos/*-shopee.md`. Estão em `status: "rascunho"`; **não ficam publicados após o merge** sem mudança explícita para `publicado`. Atenção: o texto continua visível no GitHub público.
- Preço: referência do CSV, não valor atual. Estoque não confirmado; comissão não garantida. Links 1 a 3 foram abertos manualmente pelo responsável; links 4 a 10 precisam de validação antes de ativar.
- Imagem: o CSV não inclui `image_url`; não fabricar fotografias nem puxar imagem do Mercado Livre. Concluir identidade visual com fotos reais autorizadas, quando verificadas.
- Para publicar depois da revisão: preencher data real, confirmar link e foto (se houver), mudar status, rodar `node blog/verify.cjs`, `python -m unittest discover -s tests -q` e revisar a página no navegador.
- Não existe ligação de oferta Shopee ao Radar de preços do ML. O Radar continua referenciando somente seus anúncios com evidência.
