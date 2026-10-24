# Operação automática do MiraDesconto

## Fontes e limites
O motor atual é código Python executado no GitHub Actions. Não depende de
ChatGPT aberto nem usa um buscador geral da internet.
- Catálogo: listas do proprietário em integracoes/mercadolivre/listas-afiliadas.json.
- Candidatos adicionais: API oficial Mercado Livre, busca por vendedores relacionados.
  Não é um detector de tendências nem garante acesso: 401/403 ficam no relatório.
- Preços, Radar e pauta: workflow mercadolivre-sync.yml já existente, quatro vezes por hora.
- Conteúdo editorial e artes: revisão humana antes de integrar a fila. Nenhum teste de produto é inventado.
- Novos links de afiliado: fornecidos pelo proprietário; o sistema não fabrica tags.

## Agenda (horário de Brasília)
- 08h05: descoberta de candidatos; relatório nos artefatos de descobrir-candidatos.yml.
- 09h35: até dois Pins ainda inexistentes, apenas da fila aprovada.
Os horários do GitHub Actions podem atrasar. Fila vazia ou totalmente publicada não cria Pins.

## Cadastrar e publicar
1. Adicionar o link oficial pelo workflow Cadastrar links de afiliado já existente.
2. Confirmar o guia publicado, seu link de afiliado e a arte final.
3. Acrescentar em integracoes/pinterest/fila_aprovada.json: key, slug, title,
   affiliate, image (PNG em assets/pinterest), link do guia, sha256 da arte,
   approved: true. Usar a estrutura das cinco artes finais de 23/10 já cadastradas.
4. O publicador confere arquivo, assinatura, guia local, guia no ar e Pins existentes
   (guia e link afiliado) antes de publicar. Não carrega artes antigas do config.json.

## Recuperar falhas
O estado fica em integracoes/pinterest/estado_fila.json. O publicador grava e envia
status uncertain ANTES do POST. Se houver falha, a fila inteira pausa para evitar
duplicação. Após conferir Pinterest, registrar o pinId e status published/existing,
ou remover a entrada apenas quando comprovado que o envio não aconteceu.
Falha de push interrompe antes do envio. O artefato do workflow preserva diagnóstico.
A deduplicação também ignora parâmetros utm_ em links de guias.
A checagem não prova atribuição de comissão, estoque nem correspondência de todos
os redirecionamentos da loja. Essa validação permanece no cadastro.
Os publicadores manuais antigos não devem executar simultaneamente a esta fila.

## O que não foi incluído
Busca geral Google/Bing, detecção externa de tendências, criação automática de
novos reviews, novas artes e acesso às APIs Amazon/Shopee. São integrações
separadas e não devem ser apresentadas como funcionalidades já ativas.
