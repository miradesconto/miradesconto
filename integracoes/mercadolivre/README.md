# Integração Mercado Livre

O workflow atual executa `run_sync.py`, que lê `dados/catalogo.json` e chama
`rebuild_catalog.py` para consultar páginas públicas dos links de afiliado.
Ele não usa a API oficial nem precisa de OAuth. A coleta ainda tem limitações
de associação de preços e disponibilidade; não comprova estoque.
Veja [a documentação da etapa](../../docs/ESTABILIZACAO.md).

O cadastro preserva registros fora da vitrine. O gerador comum atualiza
`produtos.js`, os lotes e os dados do blog. `catalogo-semente.json` é histórico.
O workflow roda às 9h e 21h de Brasília, apenas em main, com verificações antes
do commit. Testes de pull request não coletam preços nem fazem deploy.

## API oficial separada

`sync_catalog.py` implementa `/items/bulk` e OAuth com refresh token rotativo;
não usa `client_credentials`. Aceita `ML_ACCESS_TOKEN` ou `ML_CLIENT_ID`,
`ML_CLIENT_SECRET` e estado criptografado de refresh token
(com `ML_REFRESH_TOKEN` como bootstrap). Exige `cryptography`.

O segredo fica fora dos arquivos públicos. Esta migração não lê nem modifica
`refresh-token.enc`. O modo `--dry-run` da API pode rotacionar esse estado.
Não execute essa ferramenta para validar a migração.
