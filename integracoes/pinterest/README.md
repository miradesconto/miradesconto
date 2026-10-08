# MiraDesconto Publicador — Pinterest

App 1613942, uso interno da própria conta. Trial ativo confirmado no painel em 08/10/2026. **Publicação automática desativada.** Não existe cliente de criação de Pins nem POST /pins nesta entrega.

## OAuth oficial

Retorno salvo no painel: **http://localhost:8765/callback**. A variante com 127.0.0.1 foi recusada. O listener continua vinculado somente ao IPv4 de loopback 127.0.0.1; a UI exige Host localhost:8765.

Execute no computador do titular: `python integracoes/pinterest/oauth_ui.py`.
Cole a chave secreta do aplicativo somente no campo protegido da tela local. Ela fica em memória durante a autorização e é enviada à API oficial para trocar o código; não é gravada. Nunca cole em chats, issues ou comandos.
Clique em Continuar para o Pinterest e autorize na página oficial. Escopos: boards:read,pins:read,pins:write. Não solicitamos anúncios, cobrança ou pastas secretas.

A UI valida Host, Origin, formulário e state aleatório de uso único. O callback redireciona para /done, limpando a URL. URLs, códigos e respostas sensíveis não são registrados. A troca ocorre no servidor local.
Após conectar, Consultar pastas pela API faz GET /v5/boards. Exibe até dez pastas da primeira página; lista vazia não prova ausência de pastas. Antes de escolher destino, consultar próximas páginas quando necessário.

Tokens são gravados atomicamente fora do repositório. No Windows, DPAPI criptografa para o usuário atual; falhas impedem a gravação, sem fallback em texto puro. Em POSIX, diretório 0700 e arquivo 0600. Padrão: ~/.miradesconto/pinterest/oauth.json. PINTEREST_PRIVATE_DIR permite selecionar pasta privada externa ao checkout. Nesta execução Work usa-se work/private-pinterest fora do checkout. Não compartilhar ou sincronizar esse arquivo.

Alternativa CLI: oauth_local.py authorize usa PINTEREST_APP_SECRET do ambiente; oauth_local.py check consulta pastas. Prefira a UI para não inserir segredos em comandos. Renovação automática ainda não implementada; tokens expiram. Encerre o processo local ao concluir. Para desconectar, revogue no Pinterest e remova o arquivo privado; a revogação não apaga Pins existentes.

## Pin de monitores

`python integracoes/pinterest/preparar.py` gera três rascunhos em preview/pinterest. O workflow permanece manual, somente leitura e sem segredos. O domínio canônico é https://miradesconto.com.br/. O filtro reconhece o prefixo antigo miradesconto.github.io/miradesconto/, mas **não equivale a histórico durável nem deduplicação da API**.

pin-teste.json contém título, descrição com aviso de afiliados, link, contentId estável e arte assets/pinterest/monitor-120-144.png (1000×1500). É ilustração genérica, não fotografia de modelos. Não anuncia preço, estoque ou desconto. boardId permanece nulo; approved e publishingEnabled são false. A URL da arte é planejada: ficará pública somente depois de integrar o arquivo e validar HTTP 200.

## Standard e proteção contra duplicatas

DEMONSTRACAO.md contém o roteiro. A gravação deve mostrar OAuth e ação real da API; a UI permite demonstrar leitura de pastas sem enviar Pins. Não usar testes simulados como evidência real. Autorização, pasta e vídeo dependem do titular. O pedido Standard ainda não foi enviado.

Antes do teste de criação, implementar comando exclusivamente manual, verificado para Trial/Sandbox, com registro durável e bloqueio de concorrência. Usar contentId estável, revisão aprovada, ID remoto e estados pending/sent/unknown. Estados sent/unknown impedem reenvio inclusive após reinício. Timeout/resposta incerta exige reconciliação antes de nova tentativa; nunca repetir POST cegamente. A flag local trialOnly não prova o nível concedido pelo Pinterest.

Automação pública somente após Standard confirmado, aprovação editorial, deduplicação durável, reconciliação, renovação segura e chave geral explícita. Esta entrega não implementa caminho de envio.

## Testes

`python -m unittest discover -s tests -p 'test_pinterest*.py' -v`

Cobrem state/escopos, domínio, rascunhos, armazenamento privado, falha da criptografia, Host/Origin/CSRF, troca única e retorno limpo. Testes HTTP usam credenciais fictícias e não acessam o Pinterest.

Referências oficiais consultadas em 08/10/2026:
- https://developers.pinterest.com/docs/getting-started/connect-app/
- https://developers.pinterest.com/docs/getting-started/set-up-authentication-and-authorization/
- https://developers.pinterest.com/docs/key-concepts/access-tiers/
- https://developers.pinterest.com/docs/developer-tools/sandbox/
