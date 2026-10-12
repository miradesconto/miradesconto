# MiraDesconto — camada universal de produtos (schema 2)

## Status deste PR

**Fase 1 — pronta como rascunho editorial.** Dez artigos Markdown consomem a lista selecionada de dez anúncios da Shopee diretamente em \`_data/shopee_ofertas.csv\` por meio do include \`_includes/link-shopee.html\`. Os anúncios NÃO entram em \`dados/catalogo.json\`, \`produtos.js\`, Radar ou nos workflows de coleta do Mercado Livre.

**Fase 2 — schema e componente isolados.** \`_data/produtos_unificados.json\` tem IDs internos (\`prod_sp_...\`), metadados independentes e \`offers\` por plataforma. Sem \`image_url\` verificada, fica \`null\`; não se tenta consultar o CDN do ML. \`_includes/ofertas-multiplataforma.html\` é um componente **opt-in** para uma futura tela de comparação. Ele reconhece Shopee, ML e Amazon, mas ainda não substitui nenhum card da vitrine.

O módulo \`integracoes/multiplataforma/schema.py\` valida links por host, dados, IDs e duplicatas. \`integracoes/catalogo.py\` aceita agora os campos opcionais \`platform: "mercadolivre"\`, \`affiliate_url\` (igual ao \`affiliateUrl\` aprovado) e \`custom_image\`. Se ausentes, o catálogo ML continua byte a byte como antes. Os IDs \`MLB...\` não são renomeados, e o schemaVersion 1 legado não é convertido automaticamente.

**Fase 3 — importadores de prévia, sem publicação.** Cada parser converte seus próprios dados para o schema 2, sem modificar os arquivos ML existentes:

\`\`\`bash
python integracoes/multiplataforma/import_shopee.py _data/shopee_ofertas.csv --output /tmp/shopee-preview.json
python integracoes/multiplataforma/import_mercadolivre.py dados/catalogo.json --output /tmp/ml-preview.json
python integracoes/multiplataforma/import_amazon.py /caminho/amazon-afiliados.csv --output /tmp/amazon-preview.json
python integracoes/multiplataforma/merge.py /tmp/shopee-preview.json /tmp/ml-preview.json --output /tmp/unificado-preview.json
python -m unittest discover -s tests -q
node blog/verify.cjs
python integracoes/catalogo.py check
\`\`\`

Amazon: CSV esperado: \`asin,title,affiliate_url,price,category,description,image_url,product_url\`. O parser NÃO fabrica tag, ASIN, link ou imagem. Link direto na Amazon exige \`tag=\` informado; links \`amzn.to\` devem ser gerados pelo titular. O parser apenas valida formato, **não garante comissão**.

Shopee: aceita as colunas originais \`Item Id,Item Name,Price,Product Link,Offer Link\` ou as normalizadas. O campo \`price\` é **observação de CSV**, nunca preço confirmado. \`in_stock=null\` por padrão. Fotos não são obtidas automaticamente.

Mercado Livre: usa apenas leitura de JSON, convertendo \`name\`, \`imageUrl\`, \`affiliateUrl\` e \`priceCheck\`. A pipeline legada continua intacta.

## Evitar produtos e variantes misturados

Por padrão, cada anúncio fica isolado no ID interno \`prod_sp_{item_id}\`, \`prod_ml_{número}\` ou \`prod_amazon_{asin}\`. Para unir duas lojas no mesmo produto, **verifique manualmente marca, modelo, capacidade, cor, voltagem e variante**, então informe um JSON de mapeamento para \`--map\`, por exemplo:

\`\`\`json
{"48360418130":"prod_mouse_attack_shark_x11"}
\`\`\`

Crie um mapeamento correspondente para o anúncio equivalente do ML/Amazon. Só então execute o merge. Não confunda anúncios diferentes por similaridade de título.

## Comparação segura de preços

O componente mostra o **menor preço** somente se houver ao menos duas ofertas com \`price_status="verified"\`, \`in_stock=true\`, \`price_verified_at\` com fuso, e verificação nas últimas 24 horas do build. Com CSV sem essas evidências, só mostra botões de consulta — **não afirma melhor preço, desconto ou estoque**. A comparação depende de rebuild frequente; não configure \`in_stock=true\` a partir de CSV de afiliados.

## Antes do merge/publicação

- [ ] Confirmar os sete links Shopee ainda não testados e a correspondência exata da variante.
- [ ] Obter imagens reais e autorizadas; preencher \`image_url\`, sem fotos genéricas ou imagens inventadas.
- [ ] Revisar informações técnicas e vendedores das dez páginas; preencher data e \`status: "publicado"\` apenas quando aprovado.
- [ ] Validar em CI e visualmente desktop/mobile. Não ativar o include multioferta sem dados verificados.
- [ ] Manter PR isolado dos PRs em Draft #22 (Cloudflare), #23 (Radar/Blog) e dos trabalhos de Pinterest.
- [ ] Não mesclar na \`main\` automaticamente; atualizações do bot de preços devem continuar sem alteração.
