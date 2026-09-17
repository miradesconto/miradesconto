# Categorias e destaques

`organizacao-catalogo.json` é a fonte de organização, compartilhada pelo importador Python e pela atualização Node. Preços, nomes, imagens, IDs e links continuam vindo das fontes originais.

## Destaques

`featuredIds` é uma lista editorial explícita de até 12 IDs. A seleção inicial oferece variedade de categorias; não usa comissão, nota da loja ou desconto como garantia de qualidade. Um produto precisa ter cadastro, imagem e link de afiliado para entrar na seleção. O campo `featured` é booleano e não é derivado de `highlight`.

`highlight` preserva os selos registrados na planilha (por exemplo, “Mais vendido”). Esses selos existiam em quase todo o catálogo e **não** determinam a seleção da página inicial. Produtos fora da lista continuam acessíveis em **Todos**, na busca global e em suas categorias.

Para mudar a seleção, edite `featuredIds` e execute `node organizar_catalogo.cjs`, seguido de `node test-catalogo.cjs`. O organizador falha se a lista tiver IDs inválidos ou mais de 12 itens. Não substitui silenciosamente os escolhidos por outros produtos.

## Classificação

- `overrides`: revisão por ID para nomes ambíguos ou produtos que mencionam outros produtos.
- `rules`: regras ordenadas para o objeto vendido. Menções a compatibilidade, cor ou local de uso não devem mudar sua categoria.
- Sem correspondência segura, produtos novos ficam em `Outros` até revisão.

Exemplos: rack para TV → Casa; medidor de pressão → Saúde; Galaxy Buds → Eletrônicos; smartphone com RAM → Celulares; shampoo automotivo → Automotivo; cozinha de brinquedo → Brinquedos e bebê.

Ao adicionar uma regra, confira sua precedência e inclua regressão em `test-catalogo.cjs`. O importador `atualizar_produtos.py` usa o mesmo arquivo e preserva as correções nas próximas importações. `organizar_catalogo.cjs` atualiza `produtos.js` e os fragmentos de `catalogo/` sem reconstruir preços, imagens ou links. Depois de alterar o catálogo, execute também `node blog/build.cjs` para conferir os produtos editoriais.

## Navegação

A página abre em Destaques. Todos é um filtro separado. A busca do cabeçalho procura no catálogo completo, inclusive produtos fora de Destaques; ordenar e carregar mais respeitam o filtro ativo. Os links do blog com `?produto=ID` também abrem o catálogo completo. O logotipo limpa os filtros e retorna a Destaques. No celular, todas as categorias estão disponíveis em um seletor, sem depender de rolar uma longa faixa horizontal.
