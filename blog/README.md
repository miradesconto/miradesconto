# Blog MiraDesconto

[Como escrever e publicar](COMO-ESCREVER.md) · [Modelo de novo artigo](MODELO.md) · [Prompt editorial](PROMPT-EDITORIAL.md)

Artigos em `_artigos/*.md` são convertidos em páginas pelo Jekyll do GitHub Pages. O hub descobre arquivos automaticamente. Não execute um gerador para escrever artigos.

`rascunho` oculta o corpo no site, mostra uma chamada honesta e usa noindex. O repositório continua público. `publicado` com texto libera o artigo, dados estruturados e inclusão no sitemap. Artigos sem texto continuam como pautas.

`_data/produtos.json` espelha nomes, imagens e disponibilidade de links do catálogo. É sincronizado por `node blog/build.cjs`, pela organização do catálogo e pelo importador. Não edite esse espelho manualmente.

Validação: `node blog/verify.cjs` e `node test-catalogo.cjs`. Confira também a publicação Jekyll em Actions e os links no site após o commit.


## Regra obrigatória: sem capa, sem publicar

Um artigo **novo ou alterado** só pode receber `status: "publicado"` e `published: true` se tiver **imagem de capa local real e válida** em `/assets/`, cadastrada em `custom_image` (preferencialmente), `cover` ou `image`. Não usar placeholder, imagem inexistente, thumbnail borrada nem link temporário/externo.

Exemplo:
```yaml
custom_image: "/assets/blog/nome-da-pauta/capa.webp"
status: "publicado"
published: true
```

O verificador `python integracoes/automacao/check_blog_covers.py --base HEAD^` reprova novos/alterados que estejam publicados sem arquivo local de capa. Está ligado ao workflow **Validar catálogo e gerar prévia** e roda antes de montar a prévia Jekyll. Publicações antigas não alteradas ficam preservadas nesta etapa de migração.

**Importante:** uma checagem do GitHub Actions falha quando falta capa, mas só impede que um push direto vire site automaticamente se o fluxo de publicação exigir esse check (por exemplo, com proteção de branch e deploy dependente da validação). Não tratar CI separado como garantia de bloqueio do GitHub Pages. Até configurar esse requisito, criar o artigo como **rascunho** e só mudar para publicado após a checagem passar.

## Fluxo editorial v4.0
Antes de criar ou atualizar conteúdo, carregar integralmente `blog/PROMPT-EDITORIAL.md` e aplicar as sete etapas de inteligência comercial. Registrar fontes, datas, pontuação e decisão antes de publicar ofertas. Artigos informativos seguem as regras de preço e capa do prompt. Manter como rascunho quando houver bloqueios. O build sincroniza dados; não executa IA nem substitui a revisão editorial.
