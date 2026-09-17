# Integração Mercado Livre — MiraDesconto

Estrutura preparada para a futura integração oficial do catálogo MiraDesconto com a API do Mercado Livre.

## Objetivo

Atualizar dados reais dos anúncios do catálogo sem expor credenciais no site público.

Fluxo planejado:

1. O catálogo continua identificando cada anúncio pelo `id` (`MLB...`).
2. Um processo de atualização consulta a API do Mercado Livre fora do navegador do visitante.
3. O processo valida e grava somente dados públicos necessários para a vitrine.
4. `produtos.js` continua sendo consumido pelo site estático no GitHub Pages.
5. Credenciais, access tokens e refresh tokens nunca são gravados em `produtos.js`, HTML ou arquivos públicos.

## Variáveis previstas

Quando a aplicação do Mercado Livre estiver liberada, o processo poderá usar variáveis de ambiente/segredos como:

- `ML_CLIENT_ID`
- `ML_CLIENT_SECRET`
- `ML_REDIRECT_URI`
- `ML_ACCESS_TOKEN`
- `ML_REFRESH_TOKEN`

**Nunca coloque os valores reais dessas variáveis em arquivos versionados.**

## Estado atual

O catálogo atual é gerado por `atualizar_produtos.py`. Essa rotina lê a planilha, preserva os IDs dos anúncios, preços coletados, URLs, links de afiliado e imagens já confirmadas. A integração futura deve complementar esse fluxo, não substituir nem quebrar a vitrine atual.

## Próxima etapa

Após a criação da aplicação no DevCenter do Mercado Livre:

1. configurar a Redirect URI;
2. concluir OAuth 2.0;
3. armazenar os segredos fora do repositório público;
4. testar a API com poucos IDs do catálogo;
5. mapear os campos retornados;
6. criar atualização automatizada com validação e limites de requisição;
7. somente depois habilitar atualização periódica.

## Segurança

O MiraDesconto é hospedado como site estático no GitHub Pages. Portanto, `Client Secret`, access token e refresh token não podem ser usados diretamente no JavaScript público do site. Qualquer operação autenticada deve ocorrer em ambiente de execução protegido.
