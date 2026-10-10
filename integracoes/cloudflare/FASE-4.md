# MiraDesconto — Fase 4: publicar ofertas no Telegram

Agora: aplique a fase, publique o mesmo Worker e valide bot/canal com `--check`.
Depois ative a automação. O código está pronto; nenhum envio real foi executado
nesta entrega. O Telegram precisa de um bot e de um canal definido por você.

## 1. Aplicar e testar

Com a Fase 3 aplicada, use `fase-4.patch`; para a main original
`b75423b48d805e5946040573957d093de9e7d670`, use `fase-1-a-4.patch`.
Na raiz execute `git apply --check /caminho/do/patch` antes de `git apply`.
Alternativa: copie arquivos completos preservando pastas; não faça ambas as opções.
Se sua main mudou, revise conflitos antes de integrar. Não sobrescreva configurações
reais de URL, namespace KV e secrets com os valores desativados do pacote.

```bash
python -m pip install -r integracoes/social/requirements.txt
python -m unittest discover -s tests
cd integracoes/cloudflare
npm ci
npm test
npm run test:runtime
```

Passaram 64 testes JavaScript e 112 Python.
O runtime usa workerd/SQLite/KV local com preços simulados. Vinte reservas sociais
simultâneas produzem uma única autorização de envio. Também valida bloqueio de
resultado incerto, limite diário, recibo idempotente e preservação do cache/histórico
 e dos 100 redirects afiliados. Os testes Python simulam o Telegram: nenhum publica.

## 2. Preparar Worker e bot

Mantenha os bindings/migrações anteriores em `wrangler.toml`. Esta fase acrescenta
`SOCIAL_LEDGER` e a migração SQLite `v3-social`. Dentro de `integracoes/cloudflare`:

```bash
npm run deploy
npx wrangler secret put SOCIAL_WRITE_TOKEN
```

Use um segredo novo, aleatório e com pelo menos 32 caracteres. Guarde o mesmo valor
no GitHub Secret `MIRA_SOCIAL_WRITE_TOKEN`. Não reutilize o token administrativo da
Cloudflare nem o segredo do histórico. O Worker não recebe o token do bot Telegram.

No Telegram, crie um bot pelo [BotFather](https://t.me/BotFather). Adicione-o como
administrador do canal de ofertas, permitindo publicar mensagens. O script verifica
`getMe`, `getChat` e `getChatMember` antes de reservar/publicar, confirma que o destino
é um canal e que o bot possui `can_post_messages`.

Cadastre em GitHub → Settings → Secrets and variables → Actions:

| Tipo | Nome | Valor |
| --- | --- | --- |
| Secret | `TELEGRAM_BOT_TOKEN` | Token fornecido pelo BotFather |
| Secret | `MIRA_SOCIAL_WRITE_TOKEN` | Mesmo segredo de `SOCIAL_WRITE_TOKEN` do Worker |
| Variable | `TELEGRAM_CHAT_ID` | `@NomeDoCanal` público ou ID numérico privado `-100...` |
| Variable | `MIRA_GO_BASE_URL` | Origem HTTPS que atende `/go/*` da Fase 2 |
| Variable | `MIRA_SOCIAL_BASE_URL` | Origem HTTPS do Worker, geralmente `workers.dev` |
| Variable | `TELEGRAM_TEXT_ONLY` | `true` para somente texto; vazio para tentar foto |
| Variable | `MIRA_TELEGRAM_ENABLED` | Deixe desativada até concluir os testes abaixo |

Uma rota de domínio somente `/go/*` não atende `/api/social/*`; use `workers.dev`
para o controle de estado. URLs precisam ser origens sem caminho/query/credenciais.
Nunca coloque tokens no JavaScript, Git, argumentos de terminal, chat ou capturas.
Cadastre-os nos prompts seguros/secrets. Se um token vazar, revogue-o no BotFather.

## 3. Validar sem publicar

No ambiente local, configure as variáveis da tabela por um gerenciador de segredos
ou prompt seguro. `MIRA_TELEGRAM_ENABLED` é somente a chave do workflow.
Na raiz do repositório:

```bash
python integracoes/social/gerar_pauta.py --check
python integracoes/social/gerar_pauta.py --dry-run
python integracoes/social/gerar_pauta.py --status
```

`--check` faz somente leituras no Telegram e confere um 302 de `/go` contra o destino
oficial registrado. Não segue o redirect, não reserva e não envia. Não precisa de
oferta recente; confirma bot/canal/rota, não a renderização da foto no Telegram.
`--status` consulta o registro privado de envios; também não publica.

`--dry-run` não usa rede nem cria rascunhos locais. Mostra o payload da melhor oferta
qualificada, incluindo a URL interna. Precisa apenas de `MIRA_GO_BASE_URL`. Se o
catálogo/Radar não tiver oferta fresca, retorna `no_fresh_actionable_offer`.
Esse resultado é esperado com um snapshot antigo: não altere datas para forçar envio.

## 4. Ativar o primeiro envio e a rotina

Após validar destino, URL e texto, execute uma vez:

```bash
python integracoes/social/gerar_pauta.py
```

Isso é um envio real. Exija `posted: true` e um `messageId`; confira a publicação
no canal e seu botão de compra. Para começar somente com texto, use `--text-only`
ou `TELEGRAM_TEXT_ONLY=true`. Não use a prévia como se ela já tivesse publicado.

Depois configure `MIRA_TELEGRAM_ENABLED=true` no GitHub. O workflow existente
`mercadolivre-sync.yml`, horário, publica depois de atualizar/validar catálogo e
Radar. Uma falha social gera aviso sem interromper a atualização do site. A fase
não escreve/commita novos `pauta-do-dia.md` ou `.json`. Os antigos materiais editoriais
permanecem disponíveis, mas não são o registro de envios nem são atualizados.

## Critérios da oferta e formato

- Apenas tecnologia, anúncio registrado na Fase 2 e identidade/variação confirmadas.
- Preço verificado há até duas horas; Radar gerado há até seis horas.
- Preço e instante do Radar iguais à evidência atual do catálogo.
- Radar acionável, pelo menos seis observações e sete dias acompanhados.
- Valor no mínimo observado ou pelo menos 2% abaixo da média; nunca acima da média.
- Seleção pelo maior afastamento abaixo da média, depois maior período acompanhado.
- Indisponibilidade explícita impede envio. Estoque desconhecido não vira promessa
  de disponibilidade: o texto pede conferir estoque/frete/condições na loja.

A mensagem usa preço atual, comparação histórica, data/hora em Brasília, CTA e
aviso de comissão. Não chama a referência da loja de histórico nem promete estoque,
menor preço do mercado ou desconto personalizado. HTML é escapado; só aparece o
link absoluto interno `/go/MLB...`, também no botão de compra.

Por padrão, baixa a imagem oficial de `https://http2.mlstatic.com/...`, converte
JPEG/PNG/WebP para JPEG com Pillow e faz upload multipart via `sendPhoto`, com
legenda limitada a 1.024 unidades UTF-16 antes da publicação. Sem imagem desse host,
ou no modo texto, usa `sendMessage` com limite de 4.096. O download tem limite de 8 MB, 24 milhões de pixels e prazo; a imagem é reduzida
a até 2.000 pixels por lado. Se o download/conversão falhar, o script escolhe texto
antes de reservar e antes de qualquer POST Telegram. Não há fallback depois do
POST de foto. A publicação/renderização no canal ainda exige teste real.
Nenhuma chamada habilita transmissão paga (`allow_paid_broadcast`).

## Duplicatas e resultado incerto

O estado fica em SQLite do Durable Object, sem depender de arquivos temporários
ou commits do GitHub Actions. O canal é identificado pelo ID numérico validado,
mesmo que você troque entre `@username` e ID na configuração.

1. Validar bot/canal e o 302 registrado, sem seguir o link afiliado.
2. Reservar no Worker, persistindo a intenção antes da chamada externa.
3. Python faz um único POST Telegram com timeout e redirects desativados.
4. Salvar `sent` com `message_id`, `rejected` ou `uncertain` no registro remoto.

Máximo de uma tentativa por canal/dia de Brasília; rejeições também consomem o dia.
Uma mesma oferta (ID, variação e preço) confirmada é bloqueada por 72 horas.
Reservas pendentes ou incertas bloqueiam novos envios do canal, inclusive em outros
dias. Não expiram automaticamente. Isso privilegia evitar duplicatas: pode exigir
intervenção se o processo cair depois de reservar e antes de enviar.

O Telegram não oferece uma chave de idempotência neste contrato. Timeout, resposta
5xx, resposta inválida ou perda do recibo não provam que a mensagem não foi publicada.
Não existe garantia de exatamente uma vez; a reserva impede repetição automática.
Um erro explícito 4xx com `ok: false` é registrado como rejeição, sem reenvio automático.
429 não gera laço de novas tentativas nem envio extra de texto.

## Conferir e reconciliar uma reserva

```bash
python integracoes/social/gerar_pauta.py --status
```

Confira manualmente o canal e o horário da execução. Se a mensagem foi publicada,
anote seu ID (último número do link da mensagem) e confirme:

```bash
python integracoes/social/gerar_pauta.py --resolve ID_DA_RESERVA --outcome sent --message-id ID_DA_MENSAGEM
```

Se confirmou que não foi publicada, finalize como rejeitada:

```bash
python integracoes/social/gerar_pauta.py --resolve ID_DA_RESERVA --outcome rejected
```

Estes comandos alteram somente o registro; não enviam nem apagam mensagens Telegram.
Não marque uma reserva como rejeitada se houver dúvida: poderia liberar duplicata
em outro dia. Uma rejeição confirmada ainda conserva o limite do dia. Registros
`sent` não podem voltar para `rejected`; recibos iguais podem ser reaplicados.

## Desativar

Mude `MIRA_TELEGRAM_ENABLED` para `false`; os preços/históricos continuam funcionando.
Não exclua o Worker/objeto ou troque seu nome para contornar reservas. Não apague o
registro durável: ele mantém a proteção contra duplicatas. Antes de reativar,
resolva eventuais reservas pendentes com a conferência acima.

## Referências oficiais

- [Bot API: métodos, limites e respostas](https://core.telegram.org/bots/api)
- [BotFather e criação de bot](https://core.telegram.org/bots/features#botfather)
- [SQLite Durable Objects](https://developers.cloudflare.com/durable-objects/api/sqlite-storage-api/)

As quatro fases estão implementadas. Implantação, migração e postagem real precisam
ser executadas com as configurações do titular; não ocorreram nesta entrega.
