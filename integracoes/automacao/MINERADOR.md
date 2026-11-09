# Minerador automático de ofertas — MiraDesconto

O site carrega `/api/produtos.json` na seção "Mais ofertas para comparar", sem expor credenciais no navegador.

## Rodar localmente

```bash
python -m pip install -r integracoes/automacao/minerador-requirements.txt
cp integracoes/automacao/minerador.env.example .env
# Adicionar credenciais, se disponíveis
python integracoes/automacao/minerador_ofertas.py
```

`python integracoes/automacao/minerador_ofertas.py --publish` envia o JSON para a branch `main` com PyGithub e solicita build do GitHub Pages.

## Fontes e proteção
- Shopee: `productOfferV2`; preço e `offerLink` da API oficial quando a chave permite.
- Mercado Livre: busca `/sites/MLB/search` e Bot do Afiliado `/api/v1/product` quando `BOT_API_KEY` está definida.
- Fallback: Radar local do MiraDesconto com preço recente, ID existente e URL individual de afiliado registrada; **não cria** links.
- Caso uma fonte falhe, preserva anúncios validados anteriormente, não publica JSON vazio.
- `api/produtos.json` é um feed independente e não altera `_data/produtos.json` nem `produtos.js`.
- O workflow `.github/workflows/minerador-ofertas.yml` executa diariamente, com publicação via `GITHUB_TOKEN` somente em `main`.
- Para habilitar o Bot: contratar/ativar o módulo de API no Bot do Afiliado e configurar o secret `BOT_API_KEY` no GitHub.
- Para habilitar Shopee: configurar `SHOPEE_APP_ID` e `SHOPEE_APP_SECRET` (já usados pelo workflow Shopee existente).

Os valores vêm de terceiros e podem mudar; confirmar preço e estoque na loja.
