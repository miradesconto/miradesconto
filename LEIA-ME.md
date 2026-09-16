# Atualização de 16/09/2026

A versão atual tem 1.009 links de afiliado e 1.021 imagens reais. Os 13 produtos recusados pelo programa ficam fora da vitrine. Consulte AFILIADOS.md e IMAGENS.md. A análise abaixo descreve a planilha original, antes dessas complementações.

# MiraDesconto — próxima versão

Esta versão usa os 1.022 registros aproveitáveis da planilha, com os preços coletados em **15/09/2026**. Está preparada para publicação; o site público não foi alterado.

## Colocar no site

1. Extraia o ZIP e abra `index.html` para conferir no computador.
2. No repositório `miradesconto/miradesconto`, use **Add file → Upload files**.
3. Envie juntos **index.html, produtos.js e interface.js**, na mesma pasta do `index.html` atual. Confirme a substituição e salve o commit.

Não é necessário cadastrar os produtos um por um. A interface mantém a estrutura visual do HTML publicado em https://miradesconto.github.io/miradesconto/. Os estilos continuam no HTML. Os dados ficam em `produtos.js` e as funções em `interface.js`.

## Dados disponíveis

| Campo | Encontrado | Tratamento |
|---|---:|---|
| Produto e ID do anúncio | 1.022 | Preservados exatamente |
| Preço atual | 1.022 | Número positivo; é o preço registrado, sem consulta ao vivo |
| Preço anterior | 842 | 180 ausências mantidas como `null` |
| Desconto exibido na fonte | 845 | Preservado em `displayedDiscount` |
| Desconto calculável | 842 | Calculado a partir dos dois preços; arredondado para exibição |
| Categoria | Nenhuma coluna de origem | Classificação automática pelo nome, identificada como sugestão; casos não reconhecidos em Outros |
| Loja | Nenhuma coluna de origem | Mercado Livre identificado pelo domínio dos 1.022 links |
| URL do anúncio | 1.022 únicas | Preservadas integralmente, inclusive parâmetros e fragmentos |
| Link de afiliado confirmado | 0 | Coluna L de Escolher ofertas vazia; `affiliateUrl: null` |
| Imagens / URLs de imagem | 0 | Nenhuma imagem embutida ou URL de imagem identificada nas abas; `imageUrl: null` |
| Comissão, extras, avaliação, vendas e destaque | Disponíveis com algumas lacunas | Preservados nos dados; não apresentados como garantia de comissão ou estoque |
| Parcela | 290 | Preservada separadamente, sem substituir o preço total |

Há três percentuais de desconto sem preço anterior: permanecem nos dados como informação original, mas não geram selo de desconto. O preço anterior não foi reconstruído. Diferenças entre o desconto exibido pela loja e o cálculo dos preços podem decorrer de arredondamento.

## O que significa oferta válida aqui

São registros com nome, ID de anúncio, preço positivo e URL HTTP(S) estruturalmente válida que contém o ID correspondente, sem repetição de ID. Todos os 1.022 registros passaram. Nenhum foi excluído.

Isso **não confirma estoque, frete, variação, preço vigente ou recebimento de comissão**. A data da coleta e a necessidade de confirmação na loja aparecem no site. Os links atuais abrem os anúncios comuns; a presença de comissão na planilha não transforma esses endereços em links de afiliado.

As abas Ranking e Escolher ofertas representam os mesmos produtos e não foram somadas novamente. A ordem inicial acompanha o Ranking existente, sem criar uma nova pontuação ou prometer que são os menores preços do mercado. Não há seleção confirmada na aba Escolher ofertas: suas 20 linhas estão marcadas como Avaliar.

O SSD genérico do site anterior não foi associado a um anúncio por aproximação. Seu link curto não foi reaproveitado em outros produtos. O catálogo desta versão é exclusivamente o da planilha.

## Atualizar pela planilha

O arquivo `atualizar_produtos.py` usa apenas a biblioteca padrão do Python 3. Não exige Excel, pacotes pagos, API, servidor ou assinatura.

Com Python instalado, coloque o arquivo e a planilha na pasta extraída e execute:

```text
python atualizar_produtos.py MiraDesconto_ofertas_revisadas.xlsx
```

Depois, envie o novo `produtos.js` ao repositório. O conversor foi feito para a estrutura desta planilha: mantenha as colunas A:M da aba Produtos. Ele lê as URLs de afiliado que forem preenchidas na coluna L de Escolher ofertas, associando-as pela URL de produto da coluna K. Não gera links de afiliado automaticamente.

Para um ajuste pontual, cada produto em `produtos.js` contém `affiliateUrl`, `imageUrl` e `category`. Preencha somente com dados reais do anúncio correspondente. Uma nova conversão recria esse arquivo; alterações manuais nele precisam ser reaplicadas. O conversor atual não importa imagens nem categorias adicionais da planilha.

Para usar uma imagem real futuramente, informe sua URL HTTP(S) em `imageUrl`. A interface já contém carregamento adiado e indicação textual quando a imagem falta ou falha. Não foram geradas imagens fictícias.

## Funcionamento e custo

Busca por produto, loja e categoria, inclusive sem acentos; categorias clicáveis; ordenação por preço ou desconto; compartilhamento nativo ou cópia do link; restauração dos filtros pelo logotipo; visual adaptado ao celular. São exibidos 24 produtos inicialmente, com botão para carregar mais. Busca e ordenação sempre consideram todos os 1.022 registros.

O pacote é estático, sem dependências externas de execução ou serviços pagos. Usa a hospedagem GitHub Pages já existente e não exige domínio próprio. Nenhum serviço foi contratado. A atualização fornecida é sob demanda; não foi configurado monitoramento automático de preços.

## Verificação realizada

- Reconciliação independente dos 1.022 nomes, IDs, preços atuais, preços anteriores e URLs com a aba Produtos.
- Testes em navegador Edge: busca, categoria Games, três ordenações, estado vazio, restauração e carregamento de mais produtos.
- Compartilhamento nativo e cópia testados com simulação das APIs do navegador.
- Testes de texto com apóstrofos e HTML, URL insegura, preço ausente e falha de imagem.
- Telas de 320, 390 e 768 pixels sem transbordamento horizontal da página; revisão visual em computador e celular.
- Nenhum erro de JavaScript nos testes. Os anúncios não foram abertos um por um para confirmar disponibilidade ao vivo.

## Origem

Arquivo anexado à conversa Aula sobre sites: `MiraDesconto_ofertas_revisadas.xlsx`.

SHA-256: `1616BA1128E6E39FDEC5F30633EF814F1884494288EB3A62C343AF46FE1A76D8`.

Fontes internas: Produtos A1:M1023; Escolher ofertas A5:N25; Ranking A4:Y1026; Leia-me e Auditoria. O arquivo original foi somente lido.
