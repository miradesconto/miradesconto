# Métricas sem serviços pagos

Sem ID em `analytics-config.js`, nenhum script do Google é carregado. Cliques
geram o evento local `mira:affiliate_click` e contadores agregados em memória.
Não há armazenamento persistente, rede, identificação de visitantes nem painel
central: os números descrevem somente a página aberta e somem ao recarregar.

Para inspecionar no console: `MiraAnalytics.snapshot()`; para limpar:
`MiraAnalytics.reset()`. Os campos são `item_id` e `item_category` do catálogo
(quando encontrados), `affiliate_host`, `link_location` e `count`.
Links inseridos dinamicamente, teclado e botão central são atendidos sem bloquear
a navegação nem alterar URLs de afiliado. Cliques em redes sociais não são ofertas.

GA4 continua opcional: configurar um ID válido habilita o pedido de consentimento.
Só após aceitar é carregada a tag; recusar bloqueia novos envios. Isso não remove
cookies anteriores ou dados já enviados. Antes de ativar GA4, revisar também a
configuração da propriedade e desativar a medição otimizada automática de links,
buscas e formulários para evitar coleta extra fora dos eventos deste código.
O evento explícito não envia texto digitado, nomes, preços ou URL da oferta.

Validação: `node tests/test-analytics.cjs`.

# Redes sociais

Nenhum endereço oficial de Telegram, Instagram ou outro perfil social foi
identificado nos arquivos do repositório nesta revisão. Nenhum CTA foi adicionado
com destinos presumidos. Ao fornecer o endereço oficial, ele pode ser incluído
como link discreto sem widget externo, SDK ou assinatura.

# Prévia de compartilhamento

A home usa o PNG próprio `blog/social.png` (1200 × 630), com URL absoluta para
GitHub Pages. Redes sociais podem manter a prévia anterior em cache após publicar.
