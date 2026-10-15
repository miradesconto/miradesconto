# Gerador diário de destaques — MiraDesconto

Cole o texto abaixo no ChatGPT quando quiser atualizar a seleção. Os preços continuam vindo da automação atual em `produtos.js`; este JSON seleciona IDs e não insere preços manualmente.

> Pesquise tendências reais de tecnologia e promoções relevantes no Brasil hoje. Cruze as descobertas somente com os IDs já cadastrados no repositório `miradesconto/miradesconto`, conferindo o `produtos.js`, `_data/produtos.json`, `_data/radar.json` e `_data/ofertas_diarias.json`. Escolha até 4 IDs únicos com imagem real correspondente, link de afiliado individual válido, categoria tech e preço recentemente verificado pela política de 2 horas do `qualidade.js`. Descarte links genéricos de listas, produtos sem verificação ou imagens ilustrativas. Não invente preço, histórico, escassez, avaliações ou validação de comissão. Mantenha todos os demais arquivos, layouts, automações e estilos intactos. Responda **apenas** com o JSON completo, válido, para substituir `_data/ofertas_diarias.json`, usando rigorosamente o formato `{"updatedAt":"AAAA-MM-DD","ids":["MLB...","MLB..."]}`. Se não houver produtos comprovados, retorne `ids: []`. Sem explicações, Markdown ou comentários.

## Aplicação

A estrutura da vitrine lê `_data/ofertas_diarias.json`. Altere somente a lista de IDs, sem copiar preços: os valores são resolvidos do catálogo e têm validade máxima de duas horas. Antes de publicar, confira os URLs individuais e rode a compilação Jekyll.
