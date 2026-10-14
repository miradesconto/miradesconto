# Auditoria do site — 13/10/2026

Base: `b34f8ceb` da main. Escopo: correções de apresentação e navegação, sem merge/deploy e sem novos produtos ou artigos.

## Evidência em produção

- HTTP GET de 38 páginas: home, blog, Radar, Sobre, Transparência, Privacidade e os 32 artigos publicados descobertos no blog. Todas retornaram HTTP 200.
- 66 URLs distintas de imagens presentes nessas páginas retornaram HTTP 200 e conteúdo de imagem. Isso confirma acesso HTTP nesta execução, não a identidade da variante, licença ou disponibilidade futura.
- Nenhuma âncora interna ausente nem ID duplicado nas 38 páginas examinadas.
- Inspeção do blog e do guia de notebooks no navegador, incluindo largura de 360 px. O CTA superior do guia estava sem aparência de botão. O link `meli.la/1NguveN`, identificado no próprio código como lista, era apresentado como preço de um produto específico.
- As rotas legadas `/produtos/.../` são geradas pela coleção `_compras`; não foram removidas ou renomeadas.
- Não houve validação nova dos redirecionamentos comerciais, estoque, preços de loja, variantes ou licenças de imagem. URLs comerciais existentes foram preservadas.

## Correções propostas

1. Tratar falha de imagens no blog, corpo dos artigos, páginas de compra e Radar com texto neutro. Sem trocar a foto por outra variante e sem exibir falha enquanto a imagem ainda carrega.
2. Respeitar `imageVerifiedOnReview: false` também nas capas do blog; conservar dimensões e carregamento adiado. Corrigir o teste da fonte da foto nos produtos relacionados.
3. Estilizar o CTA superior com área de toque de pelo menos 48 px e manter divulgação de afiliado junto dele. Identificar explicitamente as duas listas conhecidas em CTAs de template e a lista do guia de notebooks.
4. Permitir quebra da navegação compartilhada em telas estreitas, aumentar área de toque, acrescentar atalho de teclado para ofertas na home e respeitar movimento reduzido.
5. Exibir horário da observação por card do Radar. Após duas horas, ou diante de data inválida/futura, remover a promessa de preço atual e o selo; manter somente referências históricas e acesso à loja. Reavaliar a cada minuto e ao retornar à aba.
6. Ligar cards do Radar a artigos já publicados sobre o mesmo ID. Preservar caminhos, dados comerciais, catálogo gerado e políticas de publicação.
7. Remover mensagem técnica de erro da vitrine, orientando o visitante a recarregar a página.

## Testes

- 76 testes Python: aprovados. O diretório temporário foi ajustado para a área de trabalho por uma limitação de permissões do ambiente Windows; nenhuma mudança nos testes para ocultar falhas.
- Todas as verificações locais do workflow de catálogo: aprovadas, incluindo saúde do site, catálogo, rotação, atualização/qualidade de preços, cobertura editorial, imagens, métricas e geração reproduzível.
- Novas regressões: imagens em carregamento/falha/recuperação/cache e limites de expiração do Radar. Executadas pelo teste visual já incluído no CI.
- Verificação do HTML gerado ampliada para navegação institucional, divulgação de listas, carregamento do tratamento de imagens e exclusão de rascunhos da descoberta.
- Em 14/10/2026, build Jekyll e CI completo aprovados no commit `bb82b8963fc4ccd4f1ceaea43468097243386fd2`: https://github.com/miradesconto/miradesconto/actions/runs/38547580913 . A revisão Gemini também passou: https://github.com/miradesconto/miradesconto/actions/runs/38547580918 .
- O primeiro build detectou uma ordenação de array incompatível com Jekyll 3.10. Corrigida por seleção explícita do artigo com menos produtos relacionados, preservando a correspondência por ID. O build corrigido passou sem alterar workflows.
- Prévia oficial do CI baixada e conferida por SHA-256: `fa1d155ed5daa95b7cf0063c75a7e230a38a86226ae57daa6419ef25dd8d8a30`. Servida apenas em `127.0.0.1` para revisão; sem publicação externa.
- Navegador: home, blog, Radar, categoria Notebooks e artigo Shopee X11 examinados em 320, 360 e 1280 px (15 combinações), com um H1 e sem transbordamento horizontal. Guia de notebooks também revisado em desktop e 360 px, incluindo botão e aviso de lista.
- Teclado: Tab encontra “Pular para as ofertas”; Enter transfere foco para `#ofertas`. Busca por Nintendo retorna um produto com ligação ao artigo do Switch 2.
- Testes de falha isolados da produção: 12 cards com datas expiradas perderam os 12 selos e passaram a mostrar “Consultar preço na loja”; imagem deliberadamente ausente foi ocultada com texto “Imagem indisponível”. Nenhuma URL de produto foi substituída.

## Bloqueios e limites

- PR #36 permanece rascunho e não foi integrado. Contém versões antigas de templates e dos três artigos Shopee já publicados por #37/#38. Exige reconciliação antes de eventual integração; os sete anúncios restantes continuam fora desta mudança.
- HTTP 200 de imagem não substitui revisão da correspondência visual de cada variante e autorização de uso.
- Não foi medido Lighthouse/Core Web Vitals de campo; dimensões explícitas e carregamento adiado são melhorias preventivas, sem promessa numérica de ganho.
- O catálogo automático pode atualizar a main durante a revisão. Revalidar o estado final antes de qualquer integração.
