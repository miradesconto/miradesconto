# Aquisição orgânica e conversão — 06/10/2026

## Auditoria inicial

Base: `a11c3b46ec84279f41f52b724f367d9c6637f3ee`. Site publicado acessível no navegador; a leitura por ferramenta de busca falhou, não significando indisponibilidade do site. Catálogo gerado com 83 registros, 12 destaques e 5 artigos publicados. A vitrine mostra somente registros recentes elegíveis, portanto seu total varia. Já existiam GA4 com consentimento, canonical, sitemap de artigos, política tech, verificação de preço e histórico por anúncio/variação. Esses mecanismos foram preservados.

Lacunas: categorias eram filtros sem páginas próprias; guias e produtos tinham poucos caminhos de descoberta; vários produtos distintos usavam a mesma lista afiliada, mas o CTA sugeria produto individual; GA4 selecionava o primeiro produto com o mesmo URL e atribuía cliques incorretamente. Não há mouses, teclados e componentes avulsos selecionados com base suficiente para uma recomendação. O catálogo contém descrições divergentes que precisam de confirmação de variante (ex.: ASUS 16 GB).

## Dez páginas priorizadas

Prioridade editorial por proximidade da decisão e produtos cadastrados, **não ranking comprovado de volume ou conversão**. Sem Search Console, Keyword Planner ou relatório de vendas não é possível afirmar quais termos vendem mais. Reordenar após medir impressões, consultas e cliques.

| Prioridade | URL | Intenção principal | Base comercial |
|---|---|---|---|
| 1 | /notebooks/ | notebook em promoção | 3 registros; lista afiliada |
| 2 | /produtos/asus-vivobook-go-15-ryzen-5/ | Vivobook Go 15 Ryzen 5 vale a pena | versões anunciadas; divergência de RAM explicitada |
| 3 | /monitores/ | monitor em promoção | Samsung S3 cadastrado |
| 4 | /produtos/samsung-essential-s3-24/ | Samsung Essential S3 24 120 Hz é bom | anúncio; código exato pendente |
| 5 | /produtos/acer-nitro-v15-rtx-4060/ | Acer Nitro V15 RTX 4060 vale a pena | título do anúncio; variante a conferir |
| 6 | /comparativos/notebook-8gb-ou-16gb/ | notebook 8 GB ou 16 GB | comparação de critérios, sem benchmark |
| 7 | /ofertas-tech/ | ofertas tech e desconto real | ponte para vitrine e histórico |
| 8 | /mouses/ | qual mouse comprar para trabalho ou jogos | guia; seleção comercial pendente |
| 9 | /teclados/ | teclado mecânico ou membrana | guia; seleção comercial pendente |
| 10 | /hardware/ | hardware em oferta e compatibilidade | guia; seleção comercial pendente |

As URLs recebem HTML estático com conteúdo útil, H1 único, H2, descrição, canonical, breadcrumb e schema CollectionPage/WebPage. Não há Review, estrelas ou Offer inventados. Schema de produto com preço/estoque não foi adicionado porque a disponibilidade é desconhecida e a coleta expira; marcação editorial representa melhor o conteúdo efetivo. URLs antigas foram mantidas e receberam links contextuais.

## Dados, histórico e manutenção

`_data/compra_products.json` guarda somente nomes, imagens, destinos oficiais, categoria e rota editorial; nenhum preço. `tests/test_compra.py` confronta esses dados com o cadastro. Ao mudar um produto no cadastro, atualizar essa seleção e conferir os links. Preços vêm de `produtos.js` e passam pelo mesmo `MiraQuality.usablePrice`, inclusive expiração enquanto a página está aberta. Falta de registro recente produz “Preço atual a confirmar na loja”.

O histórico existente é reutilizado sem regenerar observações. Sua URL agora se resolve a partir do script, funcionando em páginas aninhadas. Ausência de dados continua sendo ausência; nenhuma curva ou menor preço foi inventado. O CTA de lista é explícito na home, carrossel e novas páginas. Solicitar links individuais de afiliado para reduzir essa etapa; não montar links com tags presumidas.

## Indexação e publicação

- O sitemap inclui as dez páginas; a CI valida o HTML realmente gerado pelo Jekyll, canonicals, JSON-LD, links e âncoras.
- `robots.txt` já existe em `/miradesconto/robots.txt`, mas rastreadores procuram esse arquivo na **raiz do host**, `/robots.txt`. Um projeto GitHub Pages não controla essa raiz. Verificar a raiz do domínio e cadastrar o sitemap diretamente no Search Console; não prometer que o arquivo no subdiretório controla o rastreamento.
- Não mudar a propriedade/verificação do Google existente. Submeter `https://miradesconto.github.io/miradesconto/sitemap.xml` na propriedade correta e inspecionar uma página de categoria e uma de produto após o merge/publicação.
- PR gera prévia, sem deploy. Após merge, conferir a construção do GitHub Pages e abrir home, páginas novas e sitemap. Indexação depende do Google; sitemap não garante posição nem inclusão.

## GA4 e métricas que importam

ID existente preservado: `G-8Z1ZPKFYVG`. `affiliate_click` continua condicionado ao consentimento. Agora usa o ID explícito do cartão, evitando atribuir todos os cliques da lista ao primeiro produto. Parâmetros: `item_id`, `item_name`, `item_category`, `link_location`, `destination_type`, `content_path`, `affiliate_host`, e preço/moeda quando presentes no catálogo. Preço de evento é registro do catálogo, não receita nem garantia de preço atual. Revogar consentimento também desativa a tag na página aberta.

Na propriedade GA4, validar um clique consentido em Tempo real/DebugView. Registrar dimensões personalizadas de escopo de evento para `item_id`, `item_category`, `link_location`, `destination_type` e `content_path` se necessárias nos relatórios. A coleta no navegador não comprova recepção no painel: essa confirmação exige acesso à propriedade. Não chamar clique de `purchase`; compra e comissão só são comprovadas pelo painel de afiliados.

Medir semanalmente e comparar períodos completos de 28 dias:

1. **Search Console:** páginas indexadas/excluídas, impressões, cliques, CTR e posição por consulta/página; separar marca e buscas de compra. Primeira pergunta: as dez páginas estão descobertas e ganham impressões relevantes?
2. **GA4:** sessões orgânicas e sessões engajadas por landing page; sessões com `affiliate_click` / sessões da landing page, sempre com o mesmo escopo e segmento consentido. Quebrar por produto e destino individual/lista.
3. **Afiliados:** cliques do painel, pedidos aprovados, comissão aprovada, taxa de aprovação e comissão por clique. Não juntar usuários entre sistemas por suposição nem atribuir uma venda a uma página sem subID/relatório suportado.
4. **Diagnóstico:** impressões sem cliques → rever título e adequação à consulta; visitas sem clique afiliado → rever variante, disponibilidade e CTA; cliques sem vendas → verificar destino, preço, frete e confiança no vendedor.

Não definir meta percentual sem linha de base. Consentimento, bloqueadores e regras de atribuição explicam diferenças entre GA4 e painel comercial. Objetivo comercial é comissão aprovada; SEO e cliques são etapas intermediárias.

## Referências consultadas

- https://developers.google.com/search/docs/appearance/structured-data/product
- https://developers.google.com/search/docs/crawling-indexing/robots/intro
- https://developers.google.com/analytics/devguides/collection/ga4/events
- https://developers.google.com/analytics/devguides/collection/ga4/event-parameters
- https://www.asus.com/br/laptops/for-home/vivobook/vivobook-go-15-e1504f/
- https://www.samsung.com/br/support/
- https://www.acer.com/br-pt/support/drivers-and-manuals
