# Publicador MiraDesconto — Telegram + grupos WhatsApp

## Estado e responsabilidade dos canais

- **Telegram:** integração oficial Bot API, com até uma mensagem por execução, 3/dia e 5 dias de intervalo para o mesmo anúncio.
- **WhatsApp (grupos comuns):** o workflow gera um texto revisável como artefato \`oferta-whatsapp\` para copiar e compartilhar manualmente. **Não envia automaticamente** nem usa WhatsApp Web/QR codes.
- **Segurança de preços:** \`api/produtos.json\` não contém comprovação uniforme de preço por anúncio. Por isso o bot NÃO publica valores numéricos, percentuais de desconto, promessas de estoque ou "menor preço". O visitante confere as condições no anúncio. Não publicar anúncios com links bloqueados.
- **Estado persistente:** \`integracoes/social/estado-ofertas.json\`; a reserva é salva no GitHub **antes** do único envio à API do Telegram. Resultados incertos não são retransmitidos.
- **Ativação:** nenhuma postagem real acontece ao mesclar esta PR enquanto a variável \`MIRA_OFERTAS_ENABLED\` não for \`true\`.

## Passo 1 — criar e configurar o bot do Telegram

1. Abra [@BotFather](https://t.me/BotFather), execute \`/newbot\` e guarde o token em local seguro.
2. Adicione o bot como administrador do canal público **@MiraDesconto**, com permissão **Publicar mensagens**.
3. Em **GitHub → repositório → Settings → Secrets and variables → Actions** configure:
   - **Repository secret:** \`TELEGRAM_BOT_TOKEN\` — token do BotFather.
   - **Repository variable:** \`TELEGRAM_CHAT_ID\` = \`@MiraDesconto\` (ou ID numérico do canal, se diferente).
   - **Repository variable:** \`MIRA_OFERTAS_ENABLED\` = \`false\` inicialmente.
4. Em **Actions → MiraDesconto | Publicador Telegram e fila WhatsApp → Run workflow**, execute com a variável ainda desativada para rodar somente os testes. Para validar remotamente o bot/canal é necessário executar o comando \`check\` em ambiente com as credenciais configuradas.
5. Depois de validar o bot como administrador, altere \`MIRA_OFERTAS_ENABLED\` para \`true\`. Execute o workflow manualmente para a primeira publicação e confira o canal.

**Nunca cole o token em commits, mensagens, frontend ou logs.** Ele deve ficar apenas como GitHub Secret.

## Passo 2 — rotina automática

Agendamentos UTC de GitHub Actions: **12:15, 16:15 e 21:15**, equivalentes a **09:15, 13:15 e 18:15** em Brasília. Os horários do GitHub podem atrasar. Toda execução:

1. Testa o código e verifica as permissões de postagem no Telegram.
2. Lê \`api/produtos.json\` e recusa feed não atualizado há mais de 36 horas.
3. Seleciona produto tech com link afiliado permitido, priorizando acessórios Shopee e produtos maiores do Mercado Livre.
4. Confere o histórico de publicações (3/dia; bloqueio de 5 dias para anúncio repetido).
5. Faz commit da **reserva** no estado em main. Se o push falhar, a publicação é cancelada.
6. Faz **uma única tentativa** \`sendMessage\` na Bot API e persiste o recibo.
7. Anexa o texto para WhatsApp ao workflow em **Artifacts → oferta-whatsapp**.

Nenhuma edição é feita no catálogo, nos preços, nas URLs de afiliado ou nos workflows de mineração existentes.

## Passo 3 — WhatsApp

Abra a execução do workflow em **Actions**, baixe o artefato \`oferta-whatsapp\`, copie o texto do arquivo \`oferta-whatsapp.txt\` e cole no grupo de ofertas que você administra.

A integração oficial da Meta para grupos **não é compatível com grupos grandes comuns**. Requer uma conta comercial oficial elegível e, no modelo documentado em 2026, seus grupos têm limite de 8 participantes. Não habilitar automação via emulação de WhatsApp Web, pois pode resultar em bloqueio da conta.

## Comandos de manutenção (na raiz do repo)

\`\`\`bash
python -m unittest discover -s tests -p test_grupos_ofertas.py -v
python integracoes/social/grupos_ofertas.py preview
python integracoes/social/grupos_ofertas.py status
# O próximo comando faz apenas leituras no Telegram:
python integracoes/social/grupos_ofertas.py check
\`\`\`

\`preview\` não envia nem modifica estado. \`check\` requer \`TELEGRAM_BOT_TOKEN\` e \`TELEGRAM_CHAT_ID\` em variáveis de ambiente, sem imprimi-los.

## Riscos e observações

- O bot não tem como garantir que o link afiliado preserve exatamente o vendedor/preço escolhido; esta divergência já foi observada em anúncios de catálogo do Mercado Livre. Por isso a postagem não faz promessa de preço.
- Um timeout após envio pode significar "enviou, mas não recebemos resposta"; a reserva impede duplicata automatizada e o estado registra \`uncertain\` para revisão humana.
- Se o minerador não atualizar o feed em 36h, nenhuma oferta será disparada.
- O canal Telegram não estará ativo até os Secrets/Variables e a mesclagem da PR serem concluídos. O WhatsApp exige envio manual.
