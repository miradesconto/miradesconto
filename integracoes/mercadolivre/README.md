# Catálogo de afiliados

A descoberta de produtos usa a lista **TECNOLOGIA**: https://meli.la/1pyBZm8.
`listas-afiliadas.json` define as fontes atuais e substitui as fontes de descoberta
anteriores. Ofertas e links individuais já cadastrados são preservados. A lista
é reconhecida mesmo com um único produto. Novos produtos precisam de identidade,
imagem e preço confirmados antes de entrar na vitrine. URLs específicas copiadas
de listas usam `wid`, `source=lists` e `tracking_id` original; nenhum parâmetro
de afiliado é inventado.

O workflow `mercadolivre-sync.yml` está agendado a cada 15 minutos (minutos
8, 23, 38 e 53). Primeiro consulta a API oficial para enriquecer o catálogo,
confirmar preços de anúncios sem variações e coletar tendências e rankings.
Depois consulta as páginas públicas para preços não confirmados pela API.
O GitHub pode atrasar execuções agendadas.

O acesso por API é medido por recurso, sem presumir que o token libera anúncios
de outros vendedores. Bloqueios 403 ficam registrados; não apagam preços nem
criam estoque ou comissão presumidos. O relatório `api-status.json` e o resumo
da execução mostram as contagens reais. A pauta usa tendências recentes apenas
como um sinal adicional aos filtros existentes de preço e histórico.

Veja [API operacional](../../docs/API-MERCADOLIVRE.md) para os recursos,
autenticação, limites e consumo dos dados. A coleta pública continua verificando
ID, variação e moeda; se não confirmar o preço, preserva a evidência anterior.

Links individuais usam `affiliateUrl`. Para uma lista compartilhada, a geração
deriva `offerUrl` do `productUrl` coletado na própria lista: exige HTTPS, domínio
do Mercado Livre, `wid` igual ao ID do anúncio e `matt_tool_id` numérico. A URL
original é preservada integralmente, sem criar parâmetros de afiliado. Isso
evita que anúncios distintos abram a mesma lista. O registro
`links-afiliados.json` fixa o link aprovado por ID; a validação falha se uma
sincronização tentar substituí-lo. Isso não prova a atribuição de comissão:
confira cliques e vendas no Portal de Afiliados.

## Cadastrar produtos inéditos

Gere o link no **Portal de Afiliados → Gerador de Links** ou na **Barra de
Afiliados** do Mercado Livre. A API de preços do vendedor não cria o link de
afiliado. Para cada produto, prepare os dados abaixo em um arquivo JSON local
(não use uma URL de produto comum no campo `affiliateUrl`):

```json
[
  {
    "id": "MLB1234567890",
    "name": "Nome exato do produto",
    "category": "Casa",
    "productUrl": "https://produto.mercadolivre.com.br/MLB-1234567890-exemplo-_JM",
    "imageUrl": "https://http2.mlstatic.com/exemplo.webp",
    "affiliateUrl": "https://meli.la/SEU_LINK_GERADO"
  }
]
```

Os valores acima são apenas um molde: precisam ser substituídos por dados
reais do mesmo anúncio. O `productUrl` deve identificar o ID exato, inclusive
a variação quando houver. Use uma categoria que já exista no catálogo.

```bash
python integracoes/mercadolivre/register_products.py novos-produtos.json
python integracoes/mercadolivre/register_products.py novos-produtos.json --apply
python integracoes/catalogo.py check
```

A prévia consulta cada link e recusa IDs, links repetidos, páginas ambíguas,
variações divergentes e preço sem confirmação. `--apply` acrescenta os
produtos à reserva em `dados/catalogo.json` e seus links ao registro de
afiliados. O commit deve incluir **os dois arquivos**. Os novos itens entram
na vitrine em uma rotação semanal após nova confirmação de preço. Não coloque
credenciais, tokens ou links inventados no JSON.

Testes: `python -m unittest discover -s tests -q` e
`python integracoes/catalogo.py check`.
