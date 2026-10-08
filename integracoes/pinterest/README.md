# MiraDesconto Publicador — Pinterest

Aplicativo **1613942**, uso interno. O titular informou autorização da API
em 08/10/2026. O tipo de acesso (Trial ou Standard) deve ser confirmado no
[dashboard do Pinterest](https://developers.pinterest.com/apps/).
**Publicação pública segue desativada.** Este projeto não deve publicar
Pins sem revisão humana, registro durável de publicação e acesso Standard.

## O que já funciona

- `python integracoes/pinterest/preparar.py`: gera três rascunhos a partir de
  artigos publicados em `preview/pinterest/{fila.json,revisao.html}`.
- `integracoes/pinterest/config.json`: base canônica
  **https://miradesconto.com.br/** (sem `/miradesconto/`).
- Links publicados anteriormente sob
  `https://miradesconto.github.io/miradesconto/` são reconhecidos no filtro
  `--published-links arquivo.json`, evitando repetir Pin ao migrar domínio.
- A lista `pin-teste.json` prepara um único conteúdo editorial sem preço e
  sem disparar publicação. `boardId` e arte final ainda exigem validação.
- Workflow manual **Pinterest — preparar rascunhos**: somente leitura,
  sem segredos, com artefatos retidos por sete dias.

**Limite importante:** deduplicação da fila local NÃO equivale a proteção
contra duplicatas na API. Não existe cliente de publicação automática nesta
etapa.

## Autorizar a conta usando OAuth oficial (preparado, ainda não executado)

1. No painel do aplicativo Pinterest, configure exatamente esta Redirect URI:
   `http://127.0.0.1:8765/callback`.
   É o retorno **local** da ferramenta OAuth, não o link público do site.
   O Pinterest exige correspondência exata, inclusive protocolo, host e caminho.
   Se o painel não aceitar essa URI, não improvise nem redirecione para outra:
   será necessário um callback HTTPS privado implementado pelo Work.
2. No **computador do titular**, configure o `PINTEREST_APP_SECRET` como variável
   de ambiente privada, **fora de gravações e sem colocar em comandos
   compartilhados, GitHub Secrets expostos ou neste chat**.
3. Execute `python integracoes/pinterest/oauth_local.py authorize`. O navegador
   abre o domínio oficial `pinterest.com` para aprovação dos escopos mínimos:
   `boards:read,pins:read,pins:write`.
4. Após concluir, execute
   `python integracoes/pinterest/oauth_local.py check` para consultar as
   pastas reais. O programa não divulga tokens nem faz publicação.
5. Remova `PINTEREST_APP_SECRET` do ambiente após autorização.

O código OAuth usa `state` aleatório verificado, troca o código pelo token
via servidor local, e grava as credenciais **somente no perfil privado do
usuário** (`~/.miradesconto/pinterest/oauth.json`), fora do repositório.
Mantenha acesso ao perfil restrito e faça revogação se perder o computador.
**Não sincronize, versiona ou envie esse arquivo.** O token de acesso vence
e precisa de renovação antes de 30 dias; os refresh tokens contínuos requerem
rotação segura. O renovador e o armazenamento de produção serão feitos e
testados antes de automatizar qualquer envio.

## Teste Trial e solicitação Standard

1. Verifique se `https://miradesconto.com.br/blog/monitor-para-setup-como-comparar/`
   abre corretamente e se a arte PNG final está servida por URL HTTPS pública.
2. Execute e grave OAuth, aprovação no Pinterest, callback e `check`. Oculte
   valores de client secret, access/refresh tokens, código e state.
3. No Work, implemente `POST /v5/pins` para **um único** Pin do
   `pin-teste.json`, com board ID real, arquivo de arte final e confirmação
   explícita. No Trial, Pins criados ficam visíveis somente ao titular.
   Registre ID/resposta saneados e confira o Pin pela API/conta.
4. Grave a integração real em funcionamento, a criação do Pin e a conferência.
   Não grave credenciais, headers Authorization ou URLs com código OAuth.
5. No painel `My apps > Upgrade`, confira a política pública
   `https://miradesconto.com.br/privacidade.html`, anexe o vídeo e solicite
   Standard. A aprovação depende da análise do Pinterest.

## Proteção obrigatória antes da automação pública

- Botão de aprovação editorial do texto, link e arte.
- Identificador estável por conteúdo/campanha (não apenas URL).
- Registro durável do estado `pending|sent|failed`, ID remoto, horário e
  revisão aprovada; bloqueio de concorrência por chave.
- Reconciliar timeout/resposta incerta consultando Pins já existentes
  antes de reenviar. Nunca fazer retry cego em `POST /pins`.
- Frequência limitada e refresh/rotação de token sem logs sensíveis.
- Chave geral desativada por padrão. Publicação pública só com **Standard**.

Referências:
- https://developers.pinterest.com/docs/getting-started/connect-app/
- https://developers.pinterest.com/docs/getting-started/set-up-authentication-and-authorization/
- https://developers.pinterest.com/docs/key-concepts/access-tiers/
