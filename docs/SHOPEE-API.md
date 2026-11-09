# Integração de afiliados da Shopee

O workflow **Shopee — ofertas e diagnóstico** consulta os anúncios cadastrados em `_data/shopee_ofertas.csv`. O resultado separa preços verificados, candidatos para revisão e o status de cada operação. As credenciais vêm de `SHOPEE_APP_ID` e `SHOPEE_APP_SECRET`.

- **Ofertas** — consulta por loja e anúncio, busca por palavra, listas de produtos em alta, categorias, lojas e campanhas. Se a busca da Shopee falhar, o script procura o termo entre as ofertas que conseguiu consultar. O alcance dessa busca local é limitado à amostra.
- **Feed** — lista os feeds disponíveis e verifica a primeira página do primeiro feed com até dez registros. A prévia guarda somente a cobertura do teste. O conteúdo bruto fica restrito à exportação local opcional.
- **Links** — a opção manual `generate_links` testa a geração individual e em lote para os anúncios cadastrados. Os links já publicados continuam a ser lidos do CSV. O teste não gera links no agendamento diário.
- **Conversões** — consulta os últimos sete dias, com paginação. O log registra o estado da consulta. A exportação privada opcional grava o total líquido somente quando a paginação termina.
- **Validações** — o relatório exige um ID de validação da conta. Configure o Secret opcional `SHOPEE_VALIDATION_ID` para consultá-lo na rotina. Sem ID o relatório fica bloqueado.

Após a integração na branch principal, o GitHub Actions agenda a coleta às 08h20 de Brasília e guarda a prévia por sete dias. A primeira execução começa com a integração deste workflow na branch principal. Para pausar somente a publicação de preços, defina a variável de repositório `SHOPEE_PUBLICAR_PRECOS=false`. O workflow publica somente faixas de preço verificadas para os anúncios já cadastrados e solicita um build do GitHub Pages. Os artigos rotulam o preço com a data da consulta e mantêm o botão para conferir o valor na loja.

A rotina pública não armazena vendas, valores de comissão ou links novos. Para exportá-los de forma privada, use as credenciais como variáveis de ambiente em uma máquina de confiança e indique um caminho fora do repositório com `--private-report`. O arquivo é criado com permissão 0600. Use `--help` para ver os argumentos do script `integracoes/shopee/afiliados.py`.
