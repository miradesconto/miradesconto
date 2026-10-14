# MiraDesconto — Descoberta de candidatos (piloto, sem publicação)

## Objetivo

Descobrir **novos anúncios** de tecnologia relacionados aos produtos já monitorados, sem inventar descontos ou associar automaticamente links de afiliado.

Fontes documentadas pelo Mercado Livre (31/08/2026):

- `GET /items/bulk?ids=...` — consulta metadados de até 20 anúncios conhecidos, incluindo vendedor quando autorizado. Foi adotado o endpoint **bulk** novo, com `status_code`, `id` e `body`. Evita o antigo `/items?ids=`, cuja descontinuação está prevista para 25/10/2026.
- `GET /sites/MLB/search?seller_id=...` — consulta anúncios ativos de vendedores identificados, se a aplicação tiver acesso.
- `GET /items/{MLB_ID}/sale_price?context=channel_marketplace` — preço atual e referência informada pela loja, somente se autorizado.

Referências:
- https://developers.mercadolivre.com.br/pt_br/itens-e-buscas
- https://developers.mercadolivre.com.br/devcenter/api-de-precos

**A API de promoções de vendedores NÃO constitui um feed público garantido de descontos para afiliados.** Alguns endpoints retornam HTTP 403 para anúncios de terceiros. Não tentar contornar restrições.

## Uso

Antes de ativar: revisar/mesclar o PR correspondente. Este novo workflow só fica disponível no botão “Run workflow” depois de existir na branch padrão.

1. Abrir [Descobrir candidatos de ofertas](https://github.com/miradesconto/miradesconto/actions/workflows/descobrir-candidatos.yml).
2. Clicar em **Run workflow**; deixar `seller_ids` em branco para tentar derivar vendedores de anúncios já selecionados na vitrine. Alternativamente, preencher até seis IDs de vendedores conhecidos.
3. O job lê `ACCESS_TOKEN` já existente nos GitHub Secrets. Nunca enviar token pelo chat, URL ou commit.
4. Baixar o artefato `candidatos-mercadolivre-<run_id>` na execução. Ele contém `preview/candidatos-mercadolivre.json` e dura sete dias.

**Apenas o proprietário consegue disparar a consulta**: o workflow valida `github.actor == github.repository_owner`. Não há programação recorrente nesta fase experimental.

## Colunas/status do arquivo

- `id`, `title`, `category`, `productUrl` e `sellerId` só aparecem quando anúncio e vendedor são coerentes e a URL identifica o item exato.
- `priceStatus: unverified` = preço não confirmado; não exibir valor nem percentual.
- `priceStatus: confirmed_by_sale_price_api` = preço retornado pela API de venda; isso não prova desconto histórico nem comissão.
- `storeAdvertisedDiscountPct` é **apenas diferença para o preço de referência da loja**; não chamar de “menor preço”, “promoção real” ou economia comprovada.
- `historicalDiscountVerified: false` e `eligibleForPublication: false` até obter observações históricas do mesmo anúncio, associar link oficial do proprietário e concluir validações.
- `discoveryAccess: blocked_http_403` = sem permissão de busca; relatório não inventa resultados.
- `priceAccess: blocked_http_403` = a busca pode ter achado candidatos, mas os preços não podem ser confirmados por esse endpoint.

O resultado é **somente fila de revisão**. Nunca modifica `dados/catalogo.json`, `links-afiliados.json`, `produtos.js`, `index.html` ou artigos.

## O que precisa acontecer depois

1. Confirmar em execução manual se a conta autoriza as consultas. Em caso de 403, consultar permissões oficiais, não automatizar scraping como substituto.
2. Revisar 5 anúncios de exemplo, fotos, variações e identificação.
3. Gerar ou fornecer links de afiliado oficiais para **cada anúncio**, confirmando destino e comissão conforme regras do programa.
4. Arquivar preços verificáveis por dias suficientes para obter base histórica; o Radar existente usa ao menos seis observações em sete dias para oportunidade acionável.
5. Só depois disso criar fluxo de publicação sob revisão e avaliar agendamento. O piloto não se repete automaticamente.

## Teste offline

```bash
python -m unittest discover -s tests -p 'test_discover_candidates.py' -v
python -m py_compile integracoes/mercadolivre/discover_candidates.py
```

Os testes simulam respostas oficiais, diferenças de identidade, ausência de link de afiliado, moeda inválida e bloqueio HTTP 403. **Nenhum teste offline confirma que a API esteja liberada para a conta do MiraDesconto.**
