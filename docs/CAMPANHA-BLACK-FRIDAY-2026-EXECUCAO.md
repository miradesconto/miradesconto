# Black Friday MiraDesconto 2026 — execução editorial

Campanha: **20 a 27 de novembro de 2026**. Base de dados: `_data/black_friday.json` e `_data/ofertas_site.json`. A campanha usa uma única vitrine em `/black-friday/` e a página principal para divulgação — não abrir catálogo duplicado.

## Status e critérios

- **20 produtos cadastrados** para acompanhamento; não chamar todos de descontos confirmados.
- Preço só deve ser mostrado se a regra existente de frescor de **2 horas** o aprovar. Não tratar preço antigo, estoque desconhecido ou desconto riscado como evidência atual.
- Fotos: priorizar `_data/black_friday_images.json` (arquivo local do próprio catálogo). Foto quebrada não deve gerar card vazio.
- Pins: **sempre destino direto para o link de afiliado original**, não para o MiraDesconto. Identificar publicidade; verificar redirecionamento real, elegibilidade da conta e variante antes da aprovação.
- Blog: artigo novo só é publicado com **capa local válida** em `custom_image`; a validação de CI deve passar. Não inventar testes, especificações, descontos, vendas ou promoções.
- Preferências comerciais: Shopee para acessórios baratos; Mercado Livre para itens maiores, sem exclusividade inflexível. Não publicar imagem ruim para cumprir meta.
- As 16 pautas de Pins são **propostas**, não imagens aprovadas e não postagens enviadas.

## Calendário de oito artigos (dois publicados, seis pendentes)

| Data-alvo | Tema / busca principal | Situação |
|---|---|---|
| 20/11 | Notebook na Black Friday 2026: 7 pontos para conferir | **Publicado** `/blog/black-friday-2026-notebooks-o-que-conferir/` |
| 20/11 | Achadinhos de setup na Shopee sem gastar à toa | **Publicado** `/blog/black-friday-2026-achadinhos-setup-shopee/` |
| 21/11 | Como identificar desconto real: preço histórico, frete e cupom | **Planejado; exige capa e revisão** |
| 22/11 | Mouse, teclado e mousepad: como montar setup com pouco dinheiro | **Planejado; evitar canibalizar guia atual** |
| 23/11 | iPhone 15, 16 e Motorola: como comparar anúncios da Black Friday | **Planejado; não prometer desconto** |
| 24/11 | Monitor 120/144 Hz: portas, resolução e compatibilidade | **Planejado; conferir modelos específicos** |
| 25/11 | Presentes de tecnologia e acessórios baratos: cuidados antes de comprar | **Planejado; fotos dos produtos reais** |
| 26/11 | Checklist final da Black Friday 2026: método de escolha | **Planejado; atualizar em 27/11 se houver fatos novos** |

**Publicação de novos artigos requer:** conteúdo específico, fonte, capa local de qualidade, descrição SEO e aprovação dos testes. Os seis futuros não estão publicados.

## Pauta de 16 pins, duas ideias por dia

Cada tópico deve virar **um pin vertical 1000×1500** com arte original nítida, identidade branca/preta/verde e CTA VER OFERTA. Destino deve ser o link direto e exato da conta de afiliados. Conferir duplicidade entre `estado_afiliados.json`, estados legados e Pinterest antes de enfileirar. Nunca cadastrar `approved: true` sem arte final revisada.

| Dia | Pauta A | Pauta B |
|---|---|---|
| 20/11 | Cabo HDMI 2.1 para setup — Shopee | Mousepad grande para mesa — Shopee |
| 21/11 | Miniatura decorativa para monitor — Shopee | Kit de precisão 115 peças — Mercado Livre |
| 22/11 | Notebook Acer Aspire 5 16 GB — Mercado Livre | ASUS Vivobook Go 15 16 GB — Mercado Livre |
| 23/11 | iPhone 16 128 GB — Mercado Livre | Motorola Edge 60 Fusion — Mercado Livre |
| 24/11 | Monitor 120 Hz para setup — Mercado Livre | Suporte/base para controle PS4 — Mercado Livre |
| 25/11 | Soprador de ar para teclado — Mercado Livre | Fone Bluetooth — Shopee |
| 26/11 | Ring light com tripé — Mercado Livre | Caixa de som portátil — Mercado Livre |
| 27/11 | Teclado gamer ou periférico **ainda não publicado** — produto novo | Acessório útil da Shopee **ainda não publicado** — produto novo |

**Aviso:** temas são uma fila editorial, não promessas de ofertas específicas. Se não houver link novo original, arte boa ou canal autorizado, não publicar. O teclado Machenike já foi publicado em 20/11 e **não deve ser duplicado**.

## Operação diária

1. Conferir fotos, variantes, links e preço/estoque no anúncio.
2. Escolher **uma prioridade por vez** e só liberar quando a arte cumprir `integracoes/pinterest/PADRAO-QUALIDADE-PINS.md`.
3. Verificar duplicidade e atualizar `integracoes/pinterest/fila_afiliados.json` sem tocar no histórico.
4. Conferir execução em `.github/workflows/pinterest-afiliados-diretos.yml` e ID de pin.
5. Atualizar pauta com status **planejado / pronto / publicado / bloqueado**.

O agendamento do GitHub não cria automaticamente imagens de qualidade, links afiliados ou artigos SEO. Ele **publica apenas itens aprovados**. A pauta editorial evita dar como concluída uma postagem não enviada.
