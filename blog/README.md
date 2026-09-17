# Blog MiraDesconto

[Como escrever e publicar](COMO-ESCREVER.md) · [Modelo de novo artigo](MODELO.md)

Artigos em `_artigos/*.md` são convertidos em páginas pelo Jekyll do GitHub Pages. O hub descobre arquivos automaticamente. Não execute um gerador para escrever artigos.

`rascunho` oculta o corpo no site, mostra uma chamada honesta e usa noindex. O repositório continua público. `publicado` com texto libera o artigo, dados estruturados e inclusão no sitemap. Artigos sem texto continuam como pautas.

`_data/produtos.json` espelha nomes, imagens e disponibilidade de links do catálogo. É sincronizado por `node blog/build.cjs`, pela organização do catálogo e pelo importador. Não edite esse espelho manualmente.

Validação: `node blog/verify.cjs` e `node test-catalogo.cjs`. Confira também a publicação Jekyll em Actions e os links no site após o commit.
