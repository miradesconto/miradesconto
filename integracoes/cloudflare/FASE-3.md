# MiraDesconto — Fase 3: histórico no KV

Aplique esta fase após a Fase 2. O pacote inclui o código completo das três
fases, mas não publica na Cloudflare, não migra dados reais e não apaga originais.
A publicação no Telegram permanece para a Fase 4.

## 1. Aplicar e testar

Com a Fase 2 aplicada, use `fase-3.patch`. Para a main original
`b75423b48d805e5946040573957d093de9e7d670`, use `fase-1-a-3.patch`.
Execute `git apply --check /caminho/do/patch` antes de `git apply`.
Alternativamente, copie os arquivos preservando pastas. Escolha uma opção.
Se o repositório mudou, revise o patch em uma branch antes de integrar.

Na raiz, com Python 3.12+ e Node 22+:

```bash
python -m pip install -r integracoes/cloudflare/history-requirements.txt
python integracoes/cloudflare/build_allowlist.py
python integracoes/cloudflare/build_affiliate_links.py
python integracoes/cloudflare/build_history_allowlist.py
python -m unittest discover -s tests
python integracoes/mercadolivre/price_history.py --migrate-local --dry-run
cd integracoes/cloudflare
npm ci
npm test
npm run test:runtime
npm run test:migration
```

Os testes usam workerd, SQLite e KV locais, sem chamadas reais ao ML/Cloudflare.
A migração integral local passou com 649 arquivos e 54.920 observações, preservando
os bytes originais. Também passaram 60 testes JavaScript, 87 Python e a integração
do gráfico em JSDOM. São verificações locais; a conta real ainda precisa ser ativada.

## 2. Criar o namespace e publicar o mesmo Worker

Dentro de `integracoes/cloudflare`:

```bash
npx wrangler login
npx wrangler kv namespace create HISTORY_KV
```

Copie o ID retornado para o bloco de produção em `wrangler.toml`, removendo os
comentários das três linhas:

```toml
[[kv_namespaces]]
binding = "HISTORY_KV"
id = "ID_REAL_DO_NAMESPACE"
```

Mantenha o nome do Worker, a migração `v1` e a nova `v2-history`. Ela acrescenta
um objeto SQLite sem substituir o cache de preços existente. O ID composto de
zeros pertence somente ao ambiente local; não serve para produção.

```bash
npm run deploy
npx wrangler secret put HISTORY_WRITE_TOKEN
```

Crie um segredo aleatório com pelo menos 32 caracteres (por exemplo, com
`openssl rand -hex 32`). Cadastre o mesmo valor no GitHub Secret
`MIRA_HISTORY_WRITE_TOKEN`. Cadastre a URL de origem do Worker, sem caminho,
na GitHub Actions Variable `MIRA_HISTORY_BASE_URL`, por exemplo:
`https://miradesconto-precos.SEU_SUBDOMINIO.workers.dev`.
Não coloque o segredo no frontend, Git ou argumentos do terminal.

A rota de histórico não depende da autenticação do ML: recebe evidências que
os scripts existentes já coletaram. Configuração de preços e afiliados continua
conforme os guias anteriores. Uma rota de domínio `/go/*` não atende `/api/history/*`;
use inicialmente a origem `workers.dev` para o histórico.

## 3. Migrar preservando os originais

Configure no ambiente local `MIRA_HISTORY_BASE_URL` e `MIRA_HISTORY_WRITE_TOKEN`
por um gerenciador de segredos ou prompt seguro. Na raiz:

```bash
git archive --format=zip --output=historico-backup.zip HEAD historico
python integracoes/mercadolivre/price_history.py --migrate-local
```

O script faz POST autenticado em `/api/history/ingest`, em páginas de 64
observações; o Worker valida os registros e publica uma fotografia completa
por produto no KV. O upload é idempotente. Preços conflitantes para a mesma
observação são recusados, sem sobrescrever o registro anterior.

Confira `pendingPublication`: zero significa que todas as publicações solicitadas
foram confirmadas. Uma resposta 202 pode indicar dados salvos no SQLite com
publicação pendente por intervalo, limite diário ou falha do KV. Execute novamente
após a pausa indicada ou no próximo dia UTC; não apague os originais. A publicação
pendente acontece em uma próxima ingestão, sem cron próprio no Worker.

Opcionalmente, `--backfill` importa evidências dos snapshots Git dos últimos
180 dias; não altera suas datas para a data do commit. Execute apenas se precisar
desses registros extras. `price-history-init.yml` permite migração manual pelo
GitHub Actions, sem commit, exclusão de arquivos ou permissão de escrita no Git.

Confira um anúncio real:

```bash
curl -i -H 'Origin: https://miradesconto.com.br' 'https://miradesconto-precos.SEU_SUBDOMINIO.workers.dev/api/history/MLB4408547152'
```

Exija HTTP 200, `schemaVersion: 1`, `productId` correspondente, `currency: BRL`
e `observations` com preços/datas/variações esperados. Não há token no GET público.
O KV tem consistência eventual e cache mínimo de 60 segundos; o Worker também
armazena GETs públicos por 60 segundos. Aguarde a propagação antes da conferência.

## 4. Ativar o gráfico e encerrar os arquivos locais

Depois de conferir os dados, configure `historico-config.js`:

```javascript
window.MIRA_HISTORY_CONFIG = Object.freeze({
    apiBaseUrl: 'https://miradesconto-precos.SEU_SUBDOMINIO.workers.dev'
});
```

Execute `python integracoes/automacao/cache_bust.py`, revise e publique os arquivos
pelo fluxo habitual do GitHub Pages. Na aba Rede do navegador, abra o histórico
pelo botão de um produto: a consulta deve ir ao Worker, sem credenciais. Teste
30/90/180 dias, variação correta, ausência de dados e Worker indisponível.
O gráfico não consulta JSON local como alternativa.

Para remover os arquivos locais, há uma etapa explícita:

```bash
python integracoes/mercadolivre/price_history.py --migrate-local --cleanup-local
git diff --stat
```

Antes da primeira exclusão, o script exige publicação confirmada e lê o KV para
comparar todos os registros de todos os arquivos. Se qualquer confirmação falhar,
nenhum arquivo é removido. A leitura privada `?verify=1` ignora o cache HTTP do
Worker, mas não a consistência eventual do KV: aguarde pelo menos 60 segundos e
repita se necessário. Não remova arquivos manualmente para contornar a checagem.

Revise as exclusões; para prepará-las, use `git add -u -- historico` e faça o commit
pelo processo habitual. `.gitignore` impede novos arquivos, mas não deixa de rastrear
os antigos sozinho. Os workflows deixam de adicionar históricos aos commits.
Isso interrompe o crescimento futuro; os arquivos de commits antigos continuam
nos objetos Git. Esta fase não reescreve o histórico do repositório.

## Armazenamento e limites

KV é armazenamento persistente distribuído, com consistência eventual. Um
`HistoryWriter` com SQLite serializa as gravações e mantém as observações canônicas;
KV contém as fotografias que o gráfico lê. Usar KV sozinho para ler/modificar/gravar
arrays permitiria perda de atualizações concorrentes.

- Retenção: 180 dias; identidades, variações, moeda, datas e método são validados.
- Coleta normal: os 100 produtos publicados. `--all-products` pode armazenar outros
  produtos no SQLite, sem publicar automaticamente suas fotografias no KV.
- Publicação normal: janelas UTC de quatro horas, normalmente 600 escritas/dia para
  100 produtos. As evidências coletadas entre janelas ficam preservadas no SQLite.
- Migração inicial: uma fotografia por ID, 649 nesta base, em vez de uma escrita
  por observação. A migração ignora a janela de quatro horas, respeitando as cotas.
- Proteção: máximo de 900 tentativas de publicação por dia UTC, inclusive falhas;
  pelo menos um segundo entre tentativas para a mesma chave.

O KV Free permite 1.000 escritas e 100.000 leituras por dia e 1 GB armazenado.
A reserva de 900 é deste aplicativo, não reserva exclusiva da conta: outros usos
compartilham a cota. Migração e coleta normal no mesmo dia podem ficar pendentes.
Monitore também requisições, CPU e armazenamento de Workers/Durable Objects.
O plano gratuito não significa uso ilimitado.

`price_history.py` usa `requests` para um POST no Worker; o Worker usa o binding
KV para salvar. A API REST de KV da Cloudflare usa PUT, não POST. Esta implementação
não distribui um token administrativo da conta Cloudflare aos workflows.

O workflow horário mantém a coleta e passa a enviar o histórico remoto. Uma falha
é sinalizada sem bloquear o catálogo. O Radar lê o KV para produtos publicados;
em falha global preserva o arquivo anterior e sua data, encerrando rapidamente.
Antes de configurar a URL, o Radar ainda pode ler os arquivos locais existentes.
Gere novamente as três listas permitidas e publique o Worker quando o catálogo
mudar; `history-items.json` preserva IDs antigos após a limpeza.

## Reversão

Para suspender o gráfico remoto, deixe `historico-config.js` com URL vazia e
publique a mudança. Para interromper uploads, retire a variável de Actions.
Mantenha Worker, KV e objeto SQLite enquanto verificar os dados. Se precisar
restaurar o gráfico local antigo, restaure seu código da Fase 2 e os arquivos do
backup/commit; não apague o armazenamento remoto durante a investigação.

## Referências oficiais

- [Cotas e preço KV](https://developers.cloudflare.com/kv/platform/pricing/)
- [Limites KV](https://developers.cloudflare.com/kv/platform/limits/)
- [Consistência KV](https://developers.cloudflare.com/kv/concepts/how-kv-works/)
- [Binding de escrita KV](https://developers.cloudflare.com/kv/api/write-key-value-pairs/)
- [SQLite e transações](https://developers.cloudflare.com/durable-objects/api/sqlite-storage-api/)
- [Wrangler KV](https://developers.cloudflare.com/workers/wrangler/commands/#kv)

Somente iniciar a Fase 4 após **Prossiga**.
