# Integração Mercado Livre — MiraDesconto

A integração oficial com a API do Mercado Livre já está preparada no repositório.

## O que já existe

- Aplicação `MiraDesconto API` criada no DevCenter.
- OAuth validado.
- Script `integracoes/mercadolivre/sync_catalog.py` para consultar os anúncios em lotes pelo endpoint `/items/bulk`.
- Workflow `.github/workflows/mercadolivre-sync.yml` para executar a sincronização no GitHub Actions.
- O fluxo preserva links de afiliado e metadados editoriais já existentes.
- Credenciais nunca são gravadas no site, no JavaScript público ou nos JSONs do catálogo.

## Como a sincronização funciona

1. O GitHub Actions obtém um access token em ambiente protegido.
2. O script lê os IDs `MLB...` de `produtos.js`.
3. Consulta até 20 anúncios por chamada usando `/items/bulk`.
4. Atualiza título, preço, preço anterior, desconto, URL do produto, status e data de coleta quando a API fornece esses dados.
5. Regenera `produtos.js`, `catalogo/produtos-*.json` e `_data/produtos.json`.
6. Cria `integracoes/mercadolivre/ultimo-sync.json` com um relatório sem credenciais.
7. O GitHub Actions faz commit somente quando houver alteração real.

## Credencial necessária

O `Client ID` da aplicação não é secreto e já está configurado no workflow.

Falta apenas um segredo do repositório:

- `ML_CLIENT_SECRET`

Cadastrar em:

`Settings > Secrets and variables > Actions > New repository secret`

Nunca coloque o valor da chave secreta em um arquivo versionado.

## Autenticação

Para a automação, o script prefere o fluxo `client_credentials`, porque ele permite obter um novo access token sem precisar persistir um refresh token rotativo.

Se esse fluxo não estiver habilitado na aplicação do Mercado Livre, habilite `Client Credentials` no DevCenter.

Para testes locais, o script também aceita:

- `ML_ACCESS_TOKEN`
- `ML_REFRESH_TOKEN` como fallback

## Segurança

O MiraDesconto é um site estático no GitHub Pages. Por isso, `Client Secret`, access token e refresh token nunca devem aparecer em:

- `produtos.js`;
- HTML;
- JavaScript executado pelo navegador;
- arquivos JSON públicos;
- commits;
- prints públicos.

A chamada autenticada acontece somente dentro do GitHub Actions ou em ambiente local protegido.

## Disparo

O workflow pode ser iniciado manualmente pelo GitHub Actions. Também existe `integracoes/mercadolivre/trigger.txt`: alterar esse arquivo dispara uma sincronização sem precisar mudar o código.
