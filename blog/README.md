# Base editorial do MiraDesconto

O hub contém **pautas propostas**, não artigos publicados ou recomendações. A seleção é manual e não usa comissão, avaliação ou desconto como critério editorial. Nenhum produto foi testado para esta página.

## Atualizar

1. Atualize o catálogo pelas rotinas existentes.
2. Edite `blog/pautas.json`: categoria (`reviews`, `comparativos` ou `guias`), IDs reais, título e chamada honestos. Um único item deve ter `featured: true`.
3. Execute `node blog/build.cjs` na raiz. Não exige instalação de pacotes. O gerador cruza nome, imagem e link de afiliado com `produtos.js` e todos os fragmentos de `catalogo/`; interrompe se houver produto ausente ou divergente. Corrija a fonte ou remova a pauta obsoleta antes de publicar.
4. Versione a página gerada junto com os dados e confira imagens, busca, links e telas pequenas. Atualize a data do blog no sitemap apenas quando seu conteúdo mudar.

`index.html` é estático para indexação e leitura sem JavaScript. `blog.js` acrescenta busca sem acentos, estado vazio e tratamento de imagem indisponível. As imagens usam exatamente `imageUrl` dos produtos. A integração `?produto=ID#ofertas` abre o registro correspondente na vitrine; nenhuma chamada do hub abre diretamente um link de afiliado.

## Publicar um artigo de verdade

Somente após pesquisa: incluir autor responsável, data real de publicação e revisão, fontes com data de consulta, escopo, limitações, relações comerciais e distinção entre pesquisa documental e teste próprio. Não reutilizar avaliação da loja como nota editorial. Não afirmar consumo, desempenho, durabilidade ou vantagem sem evidências.

O artigo deve ter URL própria estável, título e descrição específicos, canonical, Open Graph, imagem com alternativa textual, navegação e aviso de afiliados junto às ações comerciais. Usar `Article` ou `BlogPosting` apenas para artigos reais; `Review`, `Offer` e notas exigem informações verificadas pertinentes. Adicionar ao sitemap. O hub atual usa somente `CollectionPage`, `Organization` e `BreadcrumbList`.

Preservar `../favicon.svg` e a base `/miradesconto/` do GitHub Pages. Os arquivos institucionais são `sobre.html`, `transparencia.html` e `privacidade.html`, na raiz.

## Validação

O arquivo `verify.cjs` faz verificações estáticas da base gerada. Execute `node blog/build.cjs && node blog/verify.cjs`. Valide também no navegador: busca por acentos e múltiplas palavras, resultado vazio e limpar; acesso às três seções; carregamento e falha de imagens; todos os CTAs de produto; largura de 320px e desktop; leitura sem JavaScript. O blog não confirma estoque ou condições comerciais ao vivo.
