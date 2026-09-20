# Categorias e destaques

O cadastro principal está em `dados/catalogo.json`. Consulte
[o procedimento de manutenção](docs/ESTABILIZACAO.md).

`organizacao-catalogo.json` guarda revisões por ID e regras ordenadas.
Execute `node organizar_catalogo.cjs` para aplicá-las ao cadastro; o gerador
compartilhado atualiza os derivados. Preços, links e imagens são preservados.
Inclua exemplos de regressão em `test-catalogo.cjs` ao mudar regras.

Os destaques seguem os primeiros 12 produtos publicados. A antiga lista
`featuredIds` foi aposentada. `highlight` preserva informação de origem.

No blog, apenas artigos publicados contam para o limite de um destaque.
Rascunhos podem referenciar itens conhecidos fora da vitrine.
