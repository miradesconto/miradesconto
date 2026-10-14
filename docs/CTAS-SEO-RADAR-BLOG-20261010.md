# MiraDesconto — Consolidação das etapas 1–4 (pré-implantação)

Data de preparo: 10/10/2026. Estado: **SOMENTE PROPOSTA EM BRANCH / PR EM RASCUNHO**. Sem autorização para merge, deploy ou publicação.

## Restrições obrigatórias

- Preservar layout, estilos, hierarquia visual, URLs, canonical, código-base e fluxo atual de venda.
- Nenhum novo botão; usar links textuais discretos apenas em espaços existentes.
- Nunca trocar link individual por lista genérica de afiliados ou misturar variantes/anúncios.
- Verificar links e destino final antes de publicar; se não houver oferta individual válida, não chamar de oferta individual.
- Nunca fixar preço no texto sem carimbo de verificação, período e condição; preço de referência da loja não é histórico.
- Não integrar ou modificar o PR #22 (Cloudflare) como parte deste PR: ele está em rascunho e toca interface.js, redirects e fluxos de afiliados.

## Etapa 1 — CTAs, transparência e urgência

- CTA de compra prioritário: **VER OFERTA NA LOJA**, dentro dos botões já existentes, quando a URL de produto/variante foi verificada.
- Alternativas contextuais aprovadas: **VER PREÇO ATUAL**, **APROVEITAR OFERTA** e **VER PREÇO NA LOJA** (somente quando apropriadas ao contexto).
- Em links a lista de afiliados, manter indicação explícita de que é lista; não rotular como oferta individual.
- Microcopy de confiança permitido: **Compra realizada na loja**, **Pagamento no site da loja**, **Confira preço e frete na loja**.
- Urgência somente demonstrável: **Preço sujeito a alteração**, **Disponibilidade sujeita à loja**, **Oferta até [data confirmada]**, **Estoque limitado na loja** (apenas com fonte/validade), **Cupom disponível nesta oferta** (verificado), **Preço verificado em [data/hora]**.
- Proibido: **Só hoje**, urgência/escassez artificial, **Compra Segura** e **Distribuidor Autorizado** sem prova editorial.
- Piloto preparado no Radar: altera texto do CTA existente sem trocar `href`, classes, posição ou atributos de rastreamento.

## Etapa 2 — Estrutura de conteúdo de fundo de funil

Modelo editorial para novos artigos ou revisão pontual dos existentes:

1. Título SEO de cauda longa e resumo direto, respondendo a intenção de compra.
2. Resposta rápida: vale a pena, para quem, e qual variante/uso.
3. Preço/momento da compra: evidência observada quando houver; nunca menor histórico sem dados.
4. CTA afiliado (somente para produto individual e variante comprovados).
5. Prós e contras honestos, separando ficha técnica de testes práticos.
6. Fontes oficiais do fabricante para conferir configuração e suporte.
7. Veredito e CTA final ou catálogo sem promessa de preço.

Perguntas obrigatórias: **Vale a pena? O preço está bom? Onde comprar com confiança?**

Implementado apenas como orientação em `blog/MODELO.md` nesta preparação. Artigos existentes não foram reescritos automaticamente.

## Etapa 3 — 32 palavras-chave aprovadas

### Lenovo IdeaPad Slim 3 — 8
- lenovo ideapad slim 3 ryzen 5 16gb 512gb menor preço
- ideapad slim 3 ryzen 5 vale a pena em 2026
- notebook lenovo ideapad slim 3 promoção pix
- ideapad slim 3 16gb 512gb onde comprar
- ideapad slim 3 memória ram pode aumentar
- ideapad slim 3 serve para estudar e trabalhar
- ideapad slim 3 tela ips ou tn qual comprar
- ideapad slim 3 ryzen 5 vs core i5

**Título alvo:** Lenovo IdeaPad Slim 3 vale a pena em 2026? Qual versão comprar e onde encontrar o melhor preço.

### Nintendo Switch 2 — 8
- nintendo switch 2 menor preço brasil
- nintendo switch 2 promoção pix
- nintendo switch 2 com jogo incluso vale a pena
- nintendo switch 2 pacote escolha seu jogo preço
- nintendo switch 2 onde comprar original
- nintendo switch 2 nacional ou importado
- nintendo switch 2 roda jogos do switch 1
- switch 2 console avulso ou com jogo

**Título alvo:** Nintendo Switch 2 em 2026: onde comprar mais barato e qual pacote vale a pena?

### iPhone 16 — 8
- iphone 16 128gb menor preço hoje
- iphone 16 original promoção pix
- iphone 16 128gb onde comprar com garantia
- iphone 16 vale a pena comprar em 2026
- iphone 16 ou iphone 15 qual compensa
- iphone 16 128gb ou 256gb qual comprar
- iphone 16 garantia apple como verificar
- iphone 16 preço bom para comprar

**Título alvo:** iPhone 16 vale a pena em 2026? Melhor preço, garantia e onde comprar.

### SmartTag2 / AirTag — 8
- samsung galaxy smarttag2 menor preço
- galaxy smarttag2 funciona no iphone
- smarttag2 funciona em qualquer android
- galaxy smarttag2 promoção pacote 4 unidades
- airtag 2 onde comprar original
- airtag segunda geração vale a pena 2026
- smart tag para mala de viagem qual comprar
- airtag ou samsung smarttag2 qual comprar

**Título alvo:** SmartTag2 ou AirTag em 2026: qual comprar para seu celular e onde encontrar ofertas?

**Regras de implantação SEO:** não criar páginas vazias, não trocar slugs/URLs existentes, não duplicar o conteúdo de guias já publicados e não prometer 'menor preço' sem dados. Validar variantes, loja e disponibilidade antes de novos artigos. Confirmar existência/especificação comercial de AirTag 2 antes de escrever uma ficha. Priorizar aperfeiçoamentos nos guias existentes.

## Etapa 4 — Radar ↔ Blog (mecanismo de conversão)

**Radar → Blog:** em cada card de oferta, procurar apenas um artigo em `site.artigos` que seja `status: publicado` e liste exatamente `item.id` em `produtos`. Se existir, exibir link **Ler análise de compra →** na linha de evidência, sem criar botão. Se não existir, não inserir link e manter os CTAs existentes.

**Blog → Radar:** o layout `_layouts/artigo.html` já apresenta `article-radar` quando há `site.data.radar.byId` para o primeiro produto do artigo. Manter esse caminho, a transparência e as opções de catálogo já existentes.

**Compra imediata:** CTA direto de loja sempre permanece visível no Radar; link ao blog é secundário, nunca substitui o destino de compra.

**Alinhamento de variante:** somente mesmo ID de anúncio em `item.id` ↔ `page.produtos`. Evitar vinculação por termos vagos, marca ou nome apenas.

**Exemplo existente:** iPhone 16 128 GB possui ID `MLB3931271317`, associado a conteúdo publicado como `iphone-15-ou-16-em-promocao.md`. Usar dados atuais gerados; nunca congelar `currentPriceText` em copy.

## Escopo exato do patch preparado

- `radar/index.html`: copy do CTA de oferta e link textual condicional a análise publicada do mesmo produto.
- `blog/MODELO.md`: referência editorial com estrutura de conversão/SEO.
- `docs/CTAS-SEO-RADAR-BLOG-20261010.md`: este plano, keywords, riscos e aceite.

Não foram alterados CSS, URLs, redirects, `interface.js`, `carrossel.js`, APIs, catálogo ou workflows.

## Validação obrigatória antes da aprovação final

- [x] Build Jekyll e Liquid aprovados pelo GitHub Actions; teste de regressão confirma link apenas para artigo publicado com ID idêntico.
- [x] Revisão da prévia renderizada com Chromium em 1440, 768, 390 e 320 px: sem rolagem horizontal indevida, sobreposição de CTAs ou links fora dos cards. **Imagens remotas não carregaram no ambiente isolado**, por isso ainda requer conferência final de imagens em produção.
- [x] Teste do HTML gerado confirma que `VER OFERTA NA LOJA` preserva `href`, `target`, `rel`, `data-item-id` e `data-link-location` conforme a fonte; **não prova a resolução externa do encurtador**.
- [x] Teste Jekyll valida, para todos os produtos destacados, que links editoriais só aparecem quando há artigo publicado contendo o ID idêntico; rascunhos e arquivados ficam excluídos pela regra de status.
- [x] Caso de várias páginas: iPhone 16 ID `MLB3931271317` aparece nos artigos publicados de comparação iPhone 15 × 16 e no guia de celulares; o link gerado no Radar aponta ao comparativo apropriado.
- [ ] Conferir manualmente anúncios individuais e parâmetros de afiliado; impedir links genéricos enganadores.
- [x] GitHub Actions executou `node blog/verify.cjs`, `node test-catalogo.cjs`, Python tests, build Jekyll, SEO e verificador do HTML gerado com sucesso; prévia estática armazenada como artefato (não publicada).
- [ ] Reconciliar com `main` e PR #22 antes de considerar merge (não antecipar a arquitetura `/go/:id`).
- [ ] Obter **aprovação final explícita** para merge/publicação. Nenhum merge ou deploy neste trabalho.

## O que ainda não foi implementado

- Padronização global de todos os CTAs: depende de auditoria das URLs/fluxos, incluindo PR #22.
- Criação/revisão dos quatro artigos-alvo: depende de comprovação de ofertas atuais, variante, fontes oficiais e revisão editorial; nenhum novo permalink neste PR.
- Automação de link dinâmico a oferta individual direta no Blog: depende da integração de redirecionamento validada; não modificar até finalizar o PR #22.
- Testes automatizados e build Jekyll: **aprovados em CI** (GitHub Actions). Revisão responsiva da prévia estática: **aprovada** em 4 resoluções, mas sem carregar imagens remotas. Testes manuais dos encurtadores e comportamento real de redirecionamento continuam pendentes.

## Registro de validação da branch — 10/10/2026

- Run GitHub Actions: https://github.com/miradesconto/miradesconto/actions/runs/38020826716 — testes de catálogo e site, Jekyll, SEO/links, regressão Radar ↔ Blog: **success**.
- Resultado do verificador: **10 cards do Radar, 10 CTAs comerciais preservados e 1 link para artigo publicado com ID correto**.
- A origem dos 10 links encurtados destacados está em `links-afiliados.json`, com `productUrl` individual e `#wid=MLB...` coerente com o ID do item. Os 10 links curtos são distintos. Isso **não confirma** que `meli.la` resolve atualmente para cada anúncio: ferramenta web não conseguiu seguir os redirecionamentos; testes manuais continuam obrigatórios.
- PR #22 (Cloudflare) não altera diretamente os quatro arquivos desta preparação, mas exige revisão da política de redirecionamentos antes da publicação.
- Revisão automatizada pelo Gemini: **skipped**; não tratar como aprovação editorial/de segurança.
- Sem merge, publicação ou deploy. Aprovação final continua necessária.

## Revisão adicional da prévia — 10/10/2026

- Artefato GitHub Actions: https://github.com/miradesconto/miradesconto/actions/runs/38020903686/artifacts/11658142210; extraído e renderizado em Chromium, com CSS real da prévia, sem rede externa.
- Foram renderizados **11 cards**, **11 CTAs primários** e **2 links editoriais** no estado mais recente do conteúdo do artefato. Esse número substitui a contagem anterior de 10/1, alterada por geração automática do Radar; não representa erro do PR.
- Em larguras de 1440 px (desktop), 768 px (tablet), 390 px (iPhone) e 320 px (celular pequeno): documento sem `scrollWidth` excedente, CTAs dentro do card, links sem sobreposição e sem erros JavaScript detectados na página estática.
- Links editoriais concretos do HTML gerado: `MLB4171634813` → `/blog/carregador-usb-c-iphone-como-escolher/`; `MLB3931271317` → `/blog/iphone-15-ou-16-em-promocao/`. Todos foram vinculados a artigos publicados pela verificação de ID do build.
- Os **11 IDs destacados** têm entradas únicas em `links-afiliados.json` com `affiliateUrl` igual ao Radar, `productUrl` com fragmento `#wid=MLB...` correspondente e registro no allowlist do PR #22 Cloudflare. Essa conferência é **estática**, não é uma prova de redirecionamento real.
- Bloqueio de acesso de rede em navegadores/ferramentas impediu carregar imagens remotas e seguir os atalhos `https://meli.la/...`. **Falta abrir e conferir manualmente** em navegador com rede, em especial destino e variante, não sendo seguro declarar esses testes aprovados.
- Observação: PR #22 continua separado. Mesmo sem conflito direto de arquivos, não concluir que comportamento de redirecionamento Cloudflare e Radar já foi integrado/testado.
- Mantido rascunho, sem merge e sem publicação.
