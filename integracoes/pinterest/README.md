# MiraDesconto Publicador — API Standard ativa

App ID: `1613942`. Nível **Standard confirmado** pelo titular em 14/10/2026.
Fluxo OAuth previsto: `http://localhost:8765/callback` (já registrado no Pinterest).
A integração roda no Python/GitHub Actions, jamais no JavaScript público do site.

## Autorizar a conta Pinterest (uma vez, no computador do titular)

1. Revise e incorpore o PR. No Windows, instale Python 3.12+ e GitHub CLI (`gh`). Faça `gh auth login` com a conta que administra `miradesconto/miradesconto`.
2. Clone o repositório ou baixe o ZIP da versão publicada; no terminal, na pasta raiz, execute:
   `python integracoes/pinterest/autorizar.py`
3. Quando solicitado, cole a **chave secreta do app** copiada diretamente do painel do Pinterest. Ela fica só na memória do processo local; o GitHub não permite reler o secret previamente cadastrado.
4. O navegador abrirá a tela OAuth. Autorize o aplicativo. Use o mesmo computador (localhost). O script verifica um `state` aleatório, troca o código no endpoint oficial e grava `PINTEREST_ACCESS_TOKEN` e `PINTEREST_REFRESH_TOKEN` em GitHub Actions Secrets via `gh`. **Não envie códigos, tokens ou chave pelo chat.**
5. Execute o workflow manual **Pinterest — validar conexão** na aba Actions. Ele somente lê usuário/pastas; nunca cria Pins.

Permissões solicitadas no OAuth: `boards:read`, `pins:read`, `pins:write`, `boards:write`.
O botão 'Gerar token' do painel do Pinterest oferece principalmente permissões de leitura e **não** substitui este fluxo.

## Renovação automática dos tokens

O workflow **Pinterest — renovar OAuth** executa semanalmente (segunda, 10:17 UTC).
Para funcionar, os Secrets necessários são:
- `PINTEREST_APP_SECRET` — já adicionado pelo titular (não verificável por esta integração);
- `PINTEREST_REFRESH_TOKEN` — preenchido pelo script acima;
- `GH_SECRETS_TOKEN` — credencial separada do GitHub com permissão mínima para alterar Actions Secrets neste repositório, usada também em fluxos antigos do projeto, se existir.

Se `GH_SECRETS_TOKEN` não estiver configurado, a renovação permanece pendente, sem publicar nada. **Nunca salve tokens no repositório, em logs, páginas ou artefatos**. Valide a renovação manualmente antes de depender do agendamento.

## Publicação manual — apenas depois do teste

O workflow **Pinterest — publicar Pin revisado** aceita um único artigo publicado, ID real da pasta, URL de arte final PNG/JPG hospedada em `https://miradesconto.com.br/` e a palavra de confirmação `PUBLICAR`.
Antes de executar, confira que tem direitos sobre a arte e que a URL é pública e correta. O conteúdo indica a possibilidade de comissão. O programa consulta Pins já existentes na conta para evitar republicar o mesmo link. Se falhar a consulta, bloqueia o envio.

**Nenhum agendamento de publicação foi habilitado.** O fluxo `Pinterest — preparar rascunhos` continua somente produzindo rascunhos sem aprovação. Não envie imagens de referência de produtos como se fossem artes finais licenciadas.

Depois de aprovar uma publicação, confira-a visualmente no Pinterest. Se a API retornar erro/incerteza, **verifique os Pins da conta antes de tentar novamente**. A API pode exigir conta Business ou permissões adicionais para contas pessoais conforme a data de criação do app.

## Reverter/revogar

Desabilite os workflows na aba Actions, revogue o aplicativo no Pinterest e remova os três Secrets Pinterest no GitHub. Isso não apaga Pins já publicados.
Documentação: https://developers.pinterest.com/docs/getting-started/set-up-authentication-and-authorization/
