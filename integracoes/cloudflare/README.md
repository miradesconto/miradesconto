# MiraDesconto — Fases 1 a 4: preços, links, histórico e Telegram na Cloudflare

Para publicação no Telegram, veja [FASE-4.md](FASE-4.md).
Para a migração de histórico e a implantação atual, veja [FASE-3.md](FASE-3.md).
Para implantação e testes da rota de compra, veja [FASE-2.md](FASE-2.md).
Este guia detalha a consulta de preços implementada na Fase 1; os guias
das fases seguintes prevalecem para os recursos acrescentados.

**Preços: testar o acesso real do ML antes de ativar `apiBaseUrl` no site.**

Este pacote contém o proxy de preços, seu cache, a integração da vitrine e a
rota de compra da Fase 2. As configurações do navegador começam desativadas
(`apiBaseUrl: ''` e `goBaseUrl: ''`).
Não houve implantação na conta Cloudflare nem alteração do site publicado.

Base inspecionada: `miradesconto/miradesconto`, main
`b75423b48d805e5946040573957d093de9e7d670`, em 09/10/2026.
Nessa versão há 100 produtos publicados e 756 cadastrados; a vitrine lê
`produtos.js`, sem fetch direto ao ML em `interface.js`.

## Como funciona

1. GitHub Pages entrega HTML, imagens e catálogo estático.
2. `precos.js`, chamado pelo `interface.js`, consulta os cards visíveis e os
   destaques pelo `GET /api/prices?ids=MLB...`, em lotes de até 20 anúncios.
3. O Worker valida origem, método, parâmetros e a lista de anúncios permitidos.
4. Um Durable Object único coordena o cache de cada ID. Lotes sobrepostos
   compartilham a consulta dos IDs já em processamento, inclusive entre regiões.
5. Em uma falta de cache, o objeto usa o multiget oficial
   `GET https://api.mercadolibre.com/items?ids=...&attributes=...`.
6. Somente dados do anúncio exato, em BRL e com variação confirmada, atualizam
   preço, referência e evidência no navegador. A consulta não altera URLs de compra.

| Idade desde a consulta ao ML | Resposta |
| --- | --- |
| Menos de 10 minutos | `HIT`: cache fresco, sem nova consulta de preços |
| De 10 até menos de 15 minutos | `STALE`: valor anterior imediato e uma revalidação em segundo plano |
| 15 minutos ou mais | Aguarda a consulta compartilhada; retorna dado novo ou erro |

Não há polling do catálogo inteiro nem cron no Worker. Sem visitantes, não há
revalidação de preços. Após receber `STALE`, a página tenta receber o resultado
atualizado em 1 minuto, enquanto estiver aberta. Abas ocultas não consultam.

O cache é de observações, não uma garantia de preço na finalização da compra.
A Cache API não replica dados entre regiões e não executa SWR automaticamente
com `cache.put`/`cache.match`. Por isso usamos um **Durable Object com SQLite**,
no mesmo `worker.js`, para coordenar as consultas. Isso não migra o histórico:
ele armazena apenas a última observação, cooldowns e, no modo OAuth, tokens.

“Uma consulta” significa uma chamada de preços por lote de IDs ainda não
atendidos naquele ciclo, compartilhada entre visitantes. Produtos diferentes,
novos ciclos e a renovação de autenticação geram chamadas adicionais. No modo
OAuth, um GET recusado com 401 pode ser repetido uma vez após renovar o token.
Não se promete entrega exatamente uma vez diante de falhas da plataforma/rede.

## Limite real encontrado no projeto

`integracoes/mercadolivre/README.md` registra 403 da rota `/sale_price` para
anúncios de outros vendedores. Esta implementação usa o multiget `/items`,
mas **seu acesso a essa rota também precisa ser validado com a aplicação real**.
Mudar o servidor da consulta não concede autorização no Mercado Livre.

O valor usado é `price` do anúncio, com `original_price` como referência quando
válida. Descontos personalizados, cupons, condições de pagamento e o preço da
finalização da compra não são inferidos. Variações usam seu próprio `price`,
sem herdar desconto da configuração principal. Quantidade positiva não é
tratada como prova de estoque exato: disponibilidade continua `unknown`.

401/403/429 não viram preço zero, dados de demonstração nem nova verificação.
O último cache válido só é servido até sua idade de 15 minutos. Se a consulta
falha, o navegador conserva o registro anterior com sua data original, retira
a indicação de preço recente e seu desconto, e avisa para conferir na loja.
Itens explicitamente indisponíveis saem da seleção normal da vitrine/banner.

## Arquivos

- `worker.js`: proxy, SWR, coordenação, cooldown, normalização e OAuth opcional.
- `wrangler.toml`: namespace SQLite e variáveis públicas da Cloudflare.
- `allowed-items.json`: identidade/variação dos anúncios publicados; sem preços.
- `build_allowlist.py`: gera a lista a partir do cadastro real.
- `package.json`/`package-lock.json`: Wrangler fixado e testes.
- Na raiz: `precos-config.js`, `precos.js`, ajustes em `interface.js`,
  `qualidade.js`, `carrossel.js` e na ordem dos scripts em `index.html`.
- Validação offline incluída no workflow já existente do catálogo.

## 1. Preparar os arquivos

O ZIP contém os arquivos novos/alterados e `fase-1.patch` contra a main acima.
Em um clone com essa mesma base, usar **uma** opção: aplicar o patch ou copiar
os arquivos respeitando as pastas. Não aplicar o patch depois de copiar.
Se a main mudou, revisar/adaptar o patch em uma branch antes de integrar.

Na raiz do repositório:

```bash
git switch -c fase-1-worker-cache
git apply --check fase-1.patch
git apply fase-1.patch
python integracoes/cloudflare/build_allowlist.py
cd integracoes/cloudflare
npm ci
npm test
npm run test:runtime
npx wrangler deploy --env="" --dry-run --outdir build-check
```

Usar Node.js 22 ou superior e Python 3.12 ou superior. Os testes não precisam
de tokens reais: o Mercado Livre é simulado. O dry-run empacota e valida os
bindings sem publicar. Um arquivo JSON pequeno de allowlist não é histórico
de preços e não cresce por visita/consulta.

## 2. Publicar e testar o Worker

Começar pelo modo `access_token`, já configurado. É adequado para validar
permissões com um token vigente; **não é uma autenticação permanente**.
O access token expira. Nenhum GitHub Secret é transferido automaticamente.

```bash
npx wrangler login
npx wrangler deploy --env=""
npx wrangler secret put ML_ACCESS_TOKEN --env=""
```

Colar o access token somente no prompt seguro do Wrangler. Não colocá-lo no
JavaScript, TOML, Git, terminal como argumento, chat ou screenshot. O primeiro
deploy cria o Worker/namespace; adicionar o secret depois habilita o acesso.
Copiar a URL `https://miradesconto-precos.SEU_SUBDOMINIO.workers.dev` retornada.
O frontend continua no GitHub Pages e não exige mudança de DNS do domínio.

Testar com um ID real da allowlist, por exemplo `MLB4408547152`:

```bash
curl -i "https://miradesconto-precos.SEU_SUBDOMINIO.workers.dev/health"
curl -i -H "Origin: https://miradesconto.com.br" "https://miradesconto-precos.SEU_SUBDOMINIO.workers.dev/api/prices?ids=MLB4408547152"
```

`/health` confirma configuração/rota; não comprova acesso ao ML. Na consulta,
exigir `items[0].code = 200`, `currency = BRL`, ID correto, preço numérico e
`checkedAt` válido. Um HTTP 200 externo pode conter erros individuais no lote:
**sempre conferir `items[].code`**, não apenas o status externo.

Repetir imediatamente: `X-Mira-Cache: HIT`, mesmo `checkedAt` e preço. Depois
de 10 minutos, esperar `STALE`; após concluir a atualização, nova consulta
deve apresentar `HIT` com `checkedAt` novo. Em cache frio, esperar `MISS`.
Após 15 minutos sem consulta, esperar `REVALIDATED` ou erro, nunca cache vencido.
Não adicionar `?nocache`, timestamps ou um parâmetro `url`: são recusados.

Para acompanhar revalidações:

```bash
npx wrangler tail --env=""
```

O evento `ml_price_revalidation` indica tamanho do lote e número de falhas.
Muitas consultas simultâneas do mesmo ID frio devem produzir uma revalidação.
Não procurar um `CF-Cache-Status: HIT`: o cache desta fase é coordenado pelo
objeto, identificado por `X-Mira-Cache` e pelo campo `items[].cache`.

Se aparecer 401: renovar/cadastrar um token válido. Se aparecer 403: confirmar
permissão da aplicação para esses anúncios; não ativar a consulta como solução
de preços frescos enquanto não houver resposta válida. 429: respeitar a pausa.
Não expor um endpoint para forçar atualização: os visitantes não podem ignorar
TTL nem escolher host/URL/rota de origem. CORS limita navegadores, não autentica
clientes de terminal; a allowlist limita os IDs que podem consumir chamadas ML.

## 3. Autenticação para uso contínuo (OAuth opcional desta Fase 1)

Para operação contínua, configurar `ML_AUTH_MODE = "oauth"` em `[vars]` do
`wrangler.toml`. Cadastrar no Worker:

```bash
npx wrangler secret put ML_CLIENT_ID --env=""
npx wrangler secret put ML_CLIENT_SECRET --env=""
npx wrangler secret put ML_REFRESH_TOKEN --env=""
npx wrangler deploy --env=""
```

Obter o par inicial pelo OAuth oficial do Mercado Livre, usando uma aplicação
dedicada ao Worker. **Não copiar para ele a cadeia de refresh tokens que outro
processo/GitHub Actions renova.** Dois renovadores da mesma cadeia podem consumir
o mesmo refresh token e invalidar a integração. Não desligar as automações
existentes de catálogo nesta fase.

O objeto renova antes da expiração, persiste o novo refresh token e serializa
renovações concorrentes. O secret `ML_REFRESH_TOKEN` é apenas a semente inicial;
o token rotacionado passa a existir no armazenamento privado do objeto.

Se uma renovação sofrer timeout ou resultado incerto, ela **não é repetida**:
o código pede nova autorização via `ML_OAUTH_REAUTHORIZE`. Gerar uma nova semente
OAuth, atualizar seu secret, incrementar `ML_AUTH_SEED_VERSION` e fazer deploy.
Um secret novo sem incrementar a versão não substitui o estado privado antigo.
Esperar terminar o cooldown anterior (até 5 minutos) e repetir a consulta.

Se não houver permissão para OAuth/acesso a anúncios, o pacote mantém fallback
seguro, mas a melhoria de frescor depende da liberação real da API. Acesso real
e rotação real de tokens ainda precisam ser verificados na conta do titular.

## 4. Ativar o frontend, somente depois dos testes reais

Na raiz, editar apenas a URL em `precos-config.js`:

```javascript
window.MIRA_PRICE_CONFIG = Object.freeze({
    apiBaseUrl: 'https://miradesconto-precos.SEU_SUBDOMINIO.workers.dev'
});
```

Atualizar os parâmetros `?v=` das referências a `precos-config.js`, `precos.js`,
`qualidade.js`, `interface.js` e `carrossel.js` no `index.html` (ou executar
`python integracoes/automacao/cache_bust.py` na raiz), revisar e integrar somente
esses arquivos e os arquivos de Fase 1. Aguardar o deploy normal do GitHub Pages.

No navegador, abrir F12 → Rede → filtrar por `prices`. Conferir:

- URL de destino no Worker, sem token em headers do navegador.
- Somente anúncios visíveis/destaques; sem consulta de todos os históricos.
- Preço atualizado com a data/hora efetiva de consulta.
- Nenhuma chamada de preço direta do navegador a `api.mercadolibre.com`.
- Preço novo corresponde ao MESMO anúncio/configuração da URL de compra.
- Banner, cards e descontos acompanham as evidências recebidas.
- Simular Worker offline na aba Rede: mensagem de falha e data original,
  sem apresentar o registro antigo como uma nova confirmação.

Para voltar imediatamente ao fluxo estático: `apiBaseUrl: ''`, atualizar `?v=`
e publicar essa alteração no GitHub Pages. Não é necessário apagar o Worker.

## Testar localmente

Criar `integracoes/cloudflare/.dev.vars.local` com um token vigente; esse
arquivo está ignorado pelo Git. Cadastrar somente `ML_ACCESS_TOKEN` no arquivo
local, sem commitar. Executar `npx wrangler dev --env local`. Para a página,
usar `http://localhost:8000` e a URL local que o Wrangler informar. Adicionar
essa URL temporariamente em `precos-config.js` e servir a raiz:

```bash
python -m http.server 8000 --bind 127.0.0.1
```

Ao terminar, desfazer a URL local. Um `file://` não é origem autorizada.
O ambiente local tem origens separadas e não deve ser publicado como produção.

## Manutenção e limites

- Após uma troca de anúncios publicados, executar `build_allowlist.py` na main
  atual e redeployar o Worker. IDs novos não entram automaticamente na allowlist;
  até o redeploy, a vitrine usa seus registros estáticos com aviso de falha.
- A allowlist preserva o ID original; não resolve preço de outro vendedor pelo
  “vencedor” do catálogo. Isso mantém a relação com o link afiliado existente.
- O armazenamento usa SQLite do Durable Object e sua API de chaves; não é o
  produto Workers KV. Nenhum histórico de preços foi migrado nesta fase.
- O plano Free tem cotas: Workers e Durable Objects não oferecem uso ilimitado.
  Cada lote encaminhado ao objeto consome uma requisição de DO. Cache de ML
  reduz chamadas ao marketplace, mas não elimina invocações ao Worker/objeto.
- Monitorar requisições, duração e leituras/escritas no painel Cloudflare.
  Na documentação consultada: DO Free tem 100 mil requisições/dia,
  13 mil GB-s/dia, 5 milhões de linhas lidas/dia, 100 mil escritas/dia e 5 GB.
  Ao ultrapassar cotas gratuitas, operações falham. Não foi ativado plano pago.
- APIs podem negar acesso mesmo com token válido; proxy não elimina bloqueios.

## Verificação da Fase 1

25 testes novos offline aprovados: concorrência (100 visitantes/1 chamada de
preços), lotes sobrepostos, cache após reinício, SWR, expiração, CORS, IDs,
variações, moeda, indisponibilidade, 401/403/429, OAuth e fallback no navegador.
Também passaram os 68 testes Python existentes e as verificações do catálogo,
evidência, classificação e analytics. O Wrangler realizou dry-run com o binding
SQLite. O smoke test `npm run test:runtime` confirmou 50 requisições concorrentes
e 1 chamada de preços no workerd com SQLite real. A integração do DOM foi
verificada com JSDOM: cards, banner, horário da consulta e falha sem desconto.
São respostas ML controladas; não comprovam autorização real do ML. A conferência
visual no navegador e os testes da conta real são passos de implantação.

## Fora desta entrega

A Fase 3 migra o histórico; seu guia prevalece para armazenamento e workflows.
A Fase 4 implementa publicação Telegram; veja seu guia de ativação e reconciliação.

## Documentação oficial consultada

- Cache API e limitações de SWR/replicação:
  https://developers.cloudflare.com/workers/runtime-apis/cache/
- Durable Objects e consistência:
  https://developers.cloudflare.com/durable-objects/concepts/what-are-durable-objects/
- Plano Free e SQLite:
  https://developers.cloudflare.com/durable-objects/platform/pricing/
- Configuração/bindings/migrações:
  https://developers.cloudflare.com/workers/wrangler/configuration/
- Estado e tarefas em segundo plano:
  https://developers.cloudflare.com/durable-objects/api/state/

Os parâmetros e campos da API ML seguem o contrato de itens usado pelo projeto.
A documentação pública específica do ML não pôde ser lida nesta sessão (403);
por isso as permissões reais e a resposta de cada anúncio são critérios de
aceitação obrigatórios antes da ativação.
