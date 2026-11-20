# Padrão premium de Pins — MiraDesconto

**Status:** diretriz oficial do projeto, aprovada em 20/11/2026.  
**Aplica-se:** a todas as próximas artes, filas, publicações manuais e automáticas do Pinterest.

## Objetivo
Pins com aparência profissional de e-commerce: nítidos, legíveis, padronizados, específicos para um produto real e sem aparência de montagem improvisada. **Melhor não publicar do que publicar arte ruim.**

## Identidade visual obrigatória
- Fundo branco ou cinza muito claro; preto para textos; verde como cor de destaque e CTA.
- Logo **MiraDesconto** legível e consistente; não recriar logotipo distorcido ou falso.
- Produto real como protagonista, em grande destaque, sem recortes serrilhados.
- Hierarquia: título curto > produto > até 3 benefícios verificáveis > botão visual **VER OFERTA**.
- Tipografia profissional, espaçamento generoso, alinhamento consistente e sem excesso de textos, badges ou efeitos.
- Em caso de imagem meramente ilustrativa, declarar isso na descrição e não insinuar que se trata da foto exata do anúncio.

## Qualidade e dimensões
- Exportar preferencialmente em **1000 × 1500 px (2:3)** ou **1500 × 2250 px (2:3)**, PNG de alta qualidade. Nunca aumentar uma thumbnail pequena só para aparentar resolução maior.
- Usar imagem-fonte nítida e suficientemente grande. Se a foto original for borrada, pixelada, comprimida, com marca d'água, ou cortada: **reprovar** e buscar outra imagem autorizada.
- Inspecionar visualmente o arquivo final em tamanho real antes de liberar. Conferir nitidez, textos, margens, fidelidade do produto, ausência de artefatos e legibilidade no celular.
- Não usar capturas de tela, miniaturas do Canva, URLs de preview temporárias ou fotos esticadas como arte final.
- Não usar imagens inventadas que apresentem outro produto como se fosse o anunciado; preferir fotos autorizadas ou composição genérica com aviso apropriado.

## Integridade comercial
- O link do pin deve levar **diretamente ao link original de afiliado do produto** no Mercado Livre ou na Shopee. **Não usar miradesconto.com.br como destino dos pins comerciais nesta campanha.**
- Manter intactos os parâmetros de atribuição; não inventar, substituir nem retirar o rastreamento.
- Verificar correspondência entre produto da arte, descrição, link, marketplace e página final antes da publicação.
- Inserir aviso claro de publicidade/afiliação. Não prometer descontos, preços, estoque ou entrega não verificados.
- Não duplicar pins já publicados; consultar estado da fila e o Pinterest antes de criar.
- Para itens baratos e acessórios, priorizar Shopee; para produtos de maior valor, priorizar Mercado Livre, conforme a estratégia comercial do projeto.

## Checklist de aprovação antes de entrar na fila
- [ ] Arte PNG vertical 2:3 com 1000×1500 px ou mais.
- [ ] Foto principal realmente nítida, autorizada e correspondente ao produto.
- [ ] Logo original e padrão branco, preto e verde respeitados.
- [ ] Título sem erros, até 3 benefícios, CTA “VER OFERTA” e margens bem definidas.
- [ ] Texto legível no celular; export final aberto e revisado visualmente.
- [ ] Link de afiliado original, ativo e de produto correspondente; canal autorizado no programa.
- [ ] Descrição SEO útil, sem alegações inventadas, com identificação comercial.
- [ ] Nenhuma duplicata ou envio incerto pendente.

**Regra de bloqueio:** se qualquer item essencial falhar, não marcar `approved: true` em `integracoes/pinterest/fila_afiliados.json`. Corrigir a arte antes de publicar. Aprovação técnica de hash/destino **não substitui** a revisão visual humana.

## Fluxo de publicação
1. Escolher um produto com link afiliado confirmado.
2. Produzir arte premium, exportar PNG final e revisar.
3. Salvar em `assets/pinterest/` e inserir o hash SHA-256, link direto e metadados na fila de afiliados.
4. Marcar `approved: true` somente depois de passar todo o checklist.
5. Publicar via `.github/workflows/pinterest-afiliados-diretos.yml`, conferir o ID do pin e o destino publicado.
6. Registrar o resultado em `integracoes/pinterest/estado_afiliados.json`.

## Orientação para futuras IAs, editores e automações
**Este arquivo é a referência permanente de qualidade para o MiraDesconto.** Não trocar o padrão visual por roxo/ciano gamer, não priorizar quantidade sobre qualidade e não rebaixar resolução para acelerar postagens. Se não houver imagem boa e link validado, deixar o pin pendente.

A automação no GitHub agenda a execução da fila; **ela não cria artes nem valida estética visual automaticamente**. Novos candidatos devem passar por revisão antes de receber aprovação.
