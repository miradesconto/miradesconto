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
5. Execute o workflow manual **Pinterest — validar conexão** na aba Actions. Ele somente lê pastas/Pins; nunca cria Pins.

Permissões solicitadas no OAuth: `boards:read`, `pins:read`, `pins:write`, `boards:write`.
O botão 'Gerar token' do painel do Pinterest oferece principalmente permissões de leitura e **não** substitui este fluxo.

## Renovação automática dos tokens

O workflow **Pinterest — renovar OAuth** executa semanalmente (segunda, 10:17 UTC).
Para funcionar, os Secrets necessários são:
- `PINTEREST_APP_SECRET` — já adicionado pelo titular (não verificável por esta integração);
- `PINTEREST_REFRESH_TOKEN` — preenchido pelo script acima;
- `GH_SECRETS_TOKEN` — credencial separada do GitHub com permissão mínima para alterar Actions Secrets neste repositório, usada também em fluxos antigos do projeto, se existir.

Se `GH_SECRETS_TOKEN` não estiver configurado, a renovação permanece pendente, sem publicar nada. **Nunca salve tokens no repositório, em logs, páginas ou artefatos**. Valide a renovação manualmente antes de depender do agendamento.

## Publicação híbrida (manual, somente após revisar)

O workflow **Pinterest — publicar Pin revisado** tem o seletor `destination`:

- `site`: preencher somente `article` (slug de artigo publicado); a URL será gerada no MiraDesconto. Deixar `affiliate_url`, `affiliate_title` e `caption` vazios.
- `mercado_livre`: preencher `affiliate_url` (link do produto gerado no programa de afiliados), `affiliate_title` e `caption`. Deixar `article` vazio. A validação aceita HTTPS em `meli.la`, `mercadolivre.com.br`, `www.mercadolivre.com.br` ou `produto.mercadolivre.com.br`. Um domínio permitido **não garante** que o link está afiliado, ativo ou aceito pelo Pinterest.

Os dois tipos exigem `board_id` real, arte PNG/JPG **própria e aprovada** hospedada em `https://miradesconto.com.br/` e `confirmation=PUBLICAR`. O sistema adiciona aviso comercial, consulta Pins existentes para evitar duplicação e bloqueia a publicação se essa consulta falhar. Não copie fotos de anúncios como artes próprias sem permissão de uso.

Antes de publicar um Pin de afiliado, confirme:
1. A conta/canal Pinterest está cadastrada e autorizada no programa de afiliados do Mercado Livre.
2. O link é realmente de afiliado e direciona ao produto correto, com anúncio ativo. Alguns destinos encurtados (`meli.la`) podem não ser aceitos pelo Pinterest; caso rejeitados, revise no programa a possibilidade de usar um link afiliado longo, sem remover os parâmetros de atribuição.
3. A arte e a legenda correspondem ao produto, informam o caráter comercial e não prometem preço, entrega ou estoque não verificados.
4. O link foi aberto, a pasta Pinterest foi selecionada e a publicação individual foi aprovada.

## Rascunhos de três ofertas do Mercado Livre

O arquivo `config.json` inclui três **sugestões não aprovadas** (Acer Aspire Go i7, Smart Tag Android e câmera A28B) com links fornecidos anteriormente pelo titular. O workflow **Pinterest — preparar rascunhos** agora gera rascunhos do site e dessas três ofertas, em JSON e HTML para revisão. Links, disponibilidade, afiliação, aprovação da plataforma e imagens finais **não foram validados por API**. Nenhuma publicação automática foi habilitada.

Depois de aprovar uma publicação, confira-a visualmente no Pinterest. Se a API retornar erro ou incerteza, verifique os Pins antes de tentar novamente. A API pode exigir conta Business ou permissões adicionais.

## Reverter/revogar

Desabilite os workflows na aba Actions, revogue o aplicativo no Pinterest e remova os três Secrets Pinterest no GitHub. Isso não apaga Pins já publicados.
Documentação: https://developers.pinterest.com/docs/getting-started/set-up-authentication-and-authorization/
