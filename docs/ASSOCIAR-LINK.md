# MiraDesconto — associação segura de links

Esta etapa amplia o painel administrativo sem substituir a API, sem gerar links de comissão e sem alterar a vitrine automaticamente.

## Como usar (depois que o PR #45 for revisado e aprovado)

1. Abra `https://miradesconto.com.br/admin/`.
2. Pesquise e selecione um produto **já cadastrado** pelo nome ou pelo ID MLB.
3. Confira o ID do anúncio e o link existente.
4. Em “Associar outro link oficial”, cole um link `meli.la` ou `mercadolivre.com.br/sec/` **gerado pela sua conta de afiliado**.
5. Use um token GitHub **restrito ao repositório** com Actions: escrita. Não compartilhe o token nem o coloque no GitHub, no chat ou em capturas de tela.
6. Clique em “Solicitar revisão do link”. Acompanhe a ação [Revisar associação de afiliado](https://github.com/miradesconto/miradesconto/actions/workflows/associate-affiliate-link.yml).
7. Se o link for validado, será criada uma branch e haverá uma tentativa de abrir um **PR em rascunho**. Reavalie o destino e os testes antes de aprovar. Configurações do GitHub podem impedir a criação automática do PR; nesse caso, a branch enviada permanece para revisão manual.

## Proteções

- A validação segue redirecionamentos somente para páginas de produto autorizadas do Mercado Livre.
- O destino precisa conter **o mesmo item e a mesma variação** do anúncio cadastrado. Links sociais e listas não são usados para vincular produtos individuais.
- Se o mesmo link já estiver associado a outro produto, a operação é recusada.
- Dados do catálogo são preservados. O link original fica registrado para auditoria na proposta.
- Um link alterado perde a confirmação do preço anterior e o produto fica temporariamente fora da vitrine. A nova publicação requer coleta confiável de preço e testes.
- O painel público **não armazena tokens**. A escrita ocorre no GitHub Actions autorizado e não pela visita ao painel.
- O fluxo não promete que a compra renderá comissão. A atribuição depende das regras do programa de afiliados.

## O que ainda NÃO está pronto

- Descoberta de promoções novas em tempo real.
- Geração automática de links pelo Mercado Livre ou Shopee.
- Edição de título, foto, variações e preços no painel.
- Confirmação real de redirecionamento com um anúncio do proprietário. Testes offline não substituem esse teste.
- Revisão visual completa da interface no celular e desktop.

## Verificação

```sh
python -m unittest discover -s tests -p 'test_associate_link.py' -v
node --check admin/associar.js
node tests/test-admin-panel.cjs
python integracoes/catalogo.py check
```

Ao criar um PR de associação, repetir o CI completo porque a sincronização de preços pode ter avançado a branch principal durante a revisão. Não mesclar dados de catálogo antigos por cima de dados novos.
