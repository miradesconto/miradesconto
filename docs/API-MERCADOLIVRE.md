# Mercado Livre: uso operacional da API

A sincronização tenta a API oficial antes da coleta pública. O acesso efetivo depende das permissões do aplicativo e da conta; a presença de um token não comprova acesso aos recursos.

| Recurso | Uso | Limite e evidência |
|---|---|---|
| `/items/{id}` | Conferir identidade, estado do anúncio, categoria e atributos | Até 40 anúncios publicados por rodada, com rotação. Estado ativo não comprova estoque. |
| `/items/{id}/sale_price` | Atualizar preços do catálogo, histórico e Radar | Somente anúncio exato ativo, BRL e sem variações; não troca vendedor nem produto de catálogo. Saltos acima de 50% ficam em revisão. |
| `/trends/MLB` e por categoria | Detectar termos tech e cruzar com o catálogo | Cache de 6 horas; pauta ignora evidência com mais de 24 horas. Não equivale a previsão de vendas. |
| `/highlights/MLB/category/{id}` | Descobrir candidatos entre os mais vendidos | Categorias obtidas dos anúncios consultados. Distingue ITEM e PRODUCT. Sem link afiliado aprovado, não publica. |
| `/users/{id}/items/search` + `/items/bulk` | Descoberta por vendedores relacionados | Workflow diário existente, relatório para revisão, no máximo 6 vendedores e 5 candidatos detalhados. |
| `/oauth/token` | Renovar acesso quando ocorrer 401 | Refresh de uso único, sem repetição cega; salva primeiro REFRESH_TOKEN, depois ACCESS_TOKEN nos Secrets. |

## Efeito no site

Os preços confirmados pela API usam a evidência `ml-sale-price-v1`, já entendida pelo catálogo, histórico e Radar. A coleta pública não sobrescreve essa evidência enquanto estiver válida (até duas horas); continua atendendo produtos para os quais a API não confirmou um preço.

A pauta mantém todos os filtros de preço, histórico, categoria e link. Um termo de tendência com correspondência por palavras inteiras acrescenta 15 pontos à seleção e aparece em `marketTrendKeywords`. Isso não autoriza publicação social nova nem transforma preço de referência em desconto histórico.

Atributos e estado dos anúncios ficam em `_data/mercadolivre_api.json`, para inspeção e consumo editorial. Não substituem automaticamente textos curados, fotos, links ou disponibilidade da vitrine. Candidatos de ranking não geram links de afiliado: a API de vendedor não é um gerador de links de afiliado.

## Operação e diagnóstico

- Rotina principal: `mercadolivre-sync.yml`, agendada nos minutos 8, 23, 38 e 53. O GitHub pode atrasar execuções.
- Os workflows que podem renovar o mesmo token compartilham a concorrência `mercadolivre-api`, sem cancelamento de execução em andamento.
- Secrets existentes: ACCESS_TOKEN, CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN, GH_SECRETS_TOKEN. O último precisa escrever Secrets para persistir a renovação. Não copiar credenciais para arquivos, logs, chat ou HTML.
- `api-status.json` registra recursos testados, falhas, contagens e candidatos; é excluído do site pelo diretório `integracoes`.
- Artefato `mercadolivre-api-<run_id>` e resumo da execução permitem conferir resultado mesmo se a coleta pública falhar depois.
- O diagnóstico manual executa as mesmas consultas oficiais sem mudar catálogo ou sinais públicos. Pode renovar OAuth quando necessário.
- 403 interrompe a família de consultas naquela rodada e fica como bloqueado. 401 tenta renovar uma vez. 429/5xx têm até duas novas tentativas; consultas têm teto de 110 chamadas e janela de quatro minutos por rodada (uma chamada já iniciada pode terminar depois).
- Uma falha da API não impede a coleta pública existente. Um workflow verde isolado não prova sucesso da API: conferir seu relatório e contagens.

## Fora do escopo de um site afiliado

Não criar/editar anúncios de vendedor, pedidos, pagamentos, mensagens, dados de compradores ou estoque. Não consultar recursos privados sem autorização nem tentar contornar 403. São operações sem utilidade para o MiraDesconto como vitrine de afiliados.

## Referências oficiais consultadas

- https://developers.mercadolivre.com.br/pt_br/itens-e-buscas (migração para bulk e busca por usuário)
- https://developers.mercadolivre.com.br/pt_br/tendencias
- https://developers.mercadolivre.com.br/pt_br/mais-vendidos-no-mercado-livre
- https://developers.mercadolivre.com.br/pt_br/api-de-precos

A documentação descreve recursos; somente uma execução autenticada comprova o acesso desta conta.
