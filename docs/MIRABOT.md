# MiraBot — primeira versão operacional

## O que faz

Importa links oficiais de afiliado do Mercado Livre pelo GitHub Actions; identifica
links já registrados, recusa URLs de produtos comuns e links falsos, confere
anúncio, categoria e preço usando o importador existente e abre **PR em rascunho**
para revisão antes de qualquer publicação. Não gera links de afiliado nem afirma
que uma comissão foi atribuída. Sem cookies, credenciais de navegador ou bypass de API.

## Como usar

1. No GitHub do MiraDesconto, acesse **Actions**.
2. Escolha **MiraBot — cadastrar links de afiliado** → **Run workflow**.
3. Cole de 1 a 20 links `https://meli.la/...` ou `https://mercadolivre.com.br/sec/...`
   gerados **na sua conta**, no portal de afiliados do Mercado Livre.
4. Deixe **aplicar** desmarcado para receber um resumo e validar os formatos.
5. Marque **aplicar** para conferir os anúncios e preparar PR. Nenhum produto
   novo será publicado antes de revisar e mesclar o PR.
6. Veja os resultados no resumo da execução e no artefato `mirabot-resumo-...`.

Novos links não podem ser convertidos a partir de URLs comuns. Consulte
https://www.mercadolivre.com.br/l/afiliados-gere-seus-links.

## 403 na API do Mercado Livre

Um HTTP 403 em `/items/{id}` ou `/items/{id}/sale_price` pode indicar falta
de escopo, validação, acesso a dados de terceiros ou bloqueio por política. Não
é um erro de programação que possamos transformar em HTTP 200. O MiraDesconto
registra `reason: permission_or_policy_restriction`, mantém a coleta pública
de cartões confirmados e evita consultar a mesma família bloqueada a cada
15 minutos. Após 24 horas, testa novamente um anúncio. O diagnóstico manual
`Mercado Livre — diagnóstico API` força um novo teste quando solicitado.

**Para solicitar acesso oficial:** abra o DevCenter/suporte do Mercado Livre e
informe: app ID, endpoint /items/{id}, data UTC, HTTP 403, o identificador de
anúncio de terceiro (sem tokens), escopos configurados e finalidade de leitura
de catálogo para site afiliado. Pergunte explicitamente quais permissões
oficiais são elegíveis e se existe API aprovada de criação de links de afiliado.
Não compartilhe tokens, cookies ou senhas.

A coleta pública de preços segue independente. A saída da API reportará o
recurso como **bloqueado**, mesmo quando a sincronização geral estiver verde.
