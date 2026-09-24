# Catálogo de afiliados

O workflow `mercadolivre-sync.yml` consulta os 500 produtos publicados a cada
hora, no minuto 17 (UTC). Às segundas-feiras, às 10h41 UTC, consulta também
os produtos cadastrados na reserva e troca até 20 itens da vitrine. O GitHub
pode atrasar execuções agendadas. O banner usa apenas preços confirmados nas
últimas 24 horas para anunciar descontos de 50% ou mais.

O preço é extraído do cartão exato do anúncio aberto pelo link `meli.la`, com
checagem de ID, variação e moeda. Se a página não confirmar o preço, o valor
antigo mantém sua data de verificação e o produto não entra na rotação. A
coleta não comprova estoque. A rota `/items/{id}/sale_price` da API retornou
403 para os anúncios de outros vendedores; `hourly_prices.py` permanece no
repositório, mas não é executado pelo workflow.

Os links de saída vêm exclusivamente de `affiliateUrl` no catálogo. O registro
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
