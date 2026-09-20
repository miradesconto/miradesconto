# Segunda etapa: associação e validade dos preços

Depende da migração do cadastro descrita em ESTABILIZACAO.md. Não acrescenta
serviço pago, banco de dados, publicação no Pinterest ou dependência Python.

## O que muda

A coleta só aceita preço no cartão HTML do item exato. IDs em rastreamento ou
em produtos vizinhos não contam. O identificador de catálogo `/p/MLB...` não é
confundido com o item do vendedor. Quando o cadastro especifica uma variação,
o cartão precisa confirmar a mesma variação. Cartões conflitantes, incompletos,
moedas diferentes ou preços condicionados dentro do bloco de preço são recusados.
Mudanças superiores a 50% frente ao preço registrado exigem revisão; não são
aceitas automaticamente. Essa comparação com o histórico é apenas uma proteção,
não prova de que o valor anterior estava correto.

Uma leitura aceita registra `priceCheck` com item, variação, valor, moeda, método
e horário. Estoque fica desconhecido (`available: null`): um cartão com preço
não comprova disponibilidade. Links afiliados, imagens e referências do produto
permanecem preservados. A coleta mantém o mínimo de 450 resultados; abaixo disso
não substitui o catálogo. Itens recusados permanecem no cadastro principal.

Na vitrine e no destaque, preços e descontos só aparecem com evidência compatível
e idade de até 24 horas. Sem isso aparece “Ver preço na loja”, mantendo o link.
A tela reavalia a validade a cada minuto. Na primeira publicação desta etapa,
os valores históricos ficam ocultos até uma coleta válida. O cadastro atual
não foi substituído por preços das amostras usadas nos testes.

A pauta social exige também disponibilidade confirmada. Como a coleta pública
não comprova estoque, a pauta fica vazia por enquanto. Os rascunhos antigos foram
regenerados para não permanecerem como sugestões atuais. A API oficial separada
remove evidências anteriores ao atualizar um produto; ela ainda não produz a
nova comprovação de preço. Não foi executada nem teve credenciais alteradas.

## Verificação e limites

Foram consultados três links existentes (camisetas, meias e creatina), somente
para leitura. Os trechos de cartões sanitizados estão em `tests/fixtures`.
Não foi realizada uma coleta real dos 675 registros: a cobertura de formatos e
a quantidade que passará pelo mínimo de 450 ainda precisam ser medidas antes
de ativar esta coleta em produção. HTML pode mudar, bloquear acessos ou omitir
condições fora do bloco reconhecido. O preço final deve ser confirmado na loja.

Os testes sem rede cobrem identidade, variação, vizinhos, conflitos, valores,
falhas e validade; os testes do cadastro cobrem preservação e geração. O navegador
foi verificado em desktop e celular, com rede externa bloqueada e dados em memória,
para busca, link afiliado, preço recente e expirado, sem erros JavaScript.
Esse teste usa a página fonte; a construção Jekyll é verificada separadamente
pelo workflow da prévia, que não publica o site.

Execute os comandos de ESTABILIZACAO.md e `node tests/test-qualidade.cjs`.
O workflow gera um ZIP do site para revisão. Antes de publicar, revisar primeiro
a etapa do cadastro, depois esta mudança; conferir atualizações em main e medir
a cobertura da coleta em uma cópia descartável. Não reduzir o mínimo de 450
apenas para fazer uma coleta incompleta passar. Uma próxima entrega pode tratar
outros formatos e uma fonte explícita de estoque, com testes próprios.
