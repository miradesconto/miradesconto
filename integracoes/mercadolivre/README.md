# Atualização horária de preços

O workflow mercadolivre-sync.yml roda na main, no minuto 17 de cada hora
(UTC e Brasília), e aceita **Run workflow** manual. O GitHub pode atrasar
execuções agendadas; não há garantia de pontualidade.

hourly_prices.py percorre os 675 registros de dados/catalogo.json, preservando
os 500 IDs publicados, ordem e artigos. Usa catalogProductId ou um identificador
explícito /p/MLB… de productUrl para consultar /products/{id} e
buy_box_winner.item_id. Sem produto de catálogo, usa itemId ou o id existente.
Não confunde /up/MLBU… com catálogo. Sem vencedor confirmado, preserva o registro.

Consulta /items/{itemId}/sale_price?context=channel_marketplace. Valida BRL e
valores positivos finitos. amount vira price; regular_amount vira oldPrice
somente se maior que price, senão null; discount é a porcentagem ou null.
Atualiza itemId, lastUpdated e priceCheck. O id interno permanece estável.
Nunca altera affiliateUrl, imagens, títulos ou seleção da vitrine.
Um link afiliado pode apontar a vendedor específico: a API não garante que
o destino acompanhe mudanças da Buy Box.

O gerador existente atualiza produtos.js, catalogo/produtos-*.json e
_data/produtos.json. Python e navegador aceitam ml-sale-price-v1 vinculada
a itemId, mantendo a validade de 24 horas. Preço inalterado não gera commit
a cada hora: a evidência e lastUpdated só mudam junto dos dados ou após
12 horas para renovar sua validade. lastUpdated significa última verificação
persistida. Falhas não renovam evidências; consultas são contadas nos logs.

## Secrets necessários

Em **Settings → Secrets and variables → Actions → New repository secret**:

| Nome exato | Conteúdo |
| --- | --- |
| CLIENT_ID | ID da aplicação Mercado Livre autorizada |
| CLIENT_SECRET | Segredo da mesma aplicação |
| ACCESS_TOKEN | Token de acesso do usuário obtido pelo OAuth Authorization Code |
| REFRESH_TOKEN | Último refresh token válido do mesmo fluxo, ainda não consumido |
| GH_SECRETS_TOKEN | Fine-grained PAT GitHub restrito a este repositório, com Secrets: Read and write e Metadata: Read |

O GITHUB_TOKEN automático não pode escrever Actions Secrets. O quinto secret
permite persistir OAuth sem tokens em disco, código, artefatos, argumentos de
processo ou logs. Não precisa de Contents: write: o commit usa GITHUB_TOKEN.
Renove o PAT antes do vencimento. Nunca coloque tokens em issues ou conversas.

Verificado em 21/09/2026: existiam somente ML_CLIENT_SECRET, ML_REFRESH_TOKEN
e ML_REFRESH_TOKEN2; os cinco nomes acima estavam ausentes. Os nomes antigos
não são usados pela rotina nova. O refresh antigo pode já ter sido consumido.
Obtenha um par atual pelo OAuth oficial, com leitura e offline_access e o
redirect URI registrado. Não use client_credentials para substituir esse fluxo.

Só renova após HTTP 401. Confere acesso a Secrets antes de consumir o refresh;
salva o novo REFRESH_TOKEN primeiro e ACCESS_TOKEN depois, imediatamente, mesmo
se a coleta posterior falhar. POST OAuth não é repetido em erro de rede por ser
de uso único. Se a resposta se perder ou a persistência falhar, refaça OAuth;
os logs orientam sem exibir tokens. Não execute diagnóstico legado com o mesmo
par de tokens enquanto a rotina horária estiver em uso.

## Erros e publicação

- GETs: timeout de 20s, até quatro tentativas para rede/429/5xx, respeitando
  Retry-After. Esperas acima de 60s encerram a consulta.
- Falhas isoladas preservam integralmente o produto. Cinco consecutivas,
  erro OAuth ou dez minutos de coleta abortam sem escrever o catálogo.
- Renderiza e valida tudo antes da escrita; testes precedem o commit.
  Sem force-push: edição concorrente que impeça push falha, e a próxima
  execução parte da main atualizada.
- Social, home e cache só são regenerados após mudança do catálogo.
- Pages usa a branch main. Como commits de GITHUB_TOKEN não acionam seu build,
  solicita /pages/builds com pages: write, inclusive para repetir publicação
  anterior que tenha falhado.
- run_sync.py, rebuild_catalog.py, sync_catalog.py e refresh-token.enc são
  legados e não são executados ou modificados pela rotina horária.

Depois de configurar Secrets: **Actions → Mercado Livre — sincronizar catálogo
→ Run workflow → main**. Confira o resumo e o build do Pages. HTTP 403 exige
verificar acesso da aplicação/usuário ou bloqueios do Mercado Livre; não é
corrigido com preços inventados ou scraping.

Testes sem credenciais: python -m unittest discover -s tests -v;
python integracoes/catalogo.py check; node tests/test-qualidade.cjs.

Documentação oficial: [preços](https://developers.mercadolivre.com.br/pt_br/api-de-precos),
[Buy Box](https://developers.mercadolivre.com.br/concorrencia-em-catalogo),
[OAuth](https://developers.mercadolivre.com.br/autenticacao-e-autorizacao),
[permissões GitHub](https://docs.github.com/en/rest/authentication/permissions-required-for-fine-grained-personal-access-tokens).
