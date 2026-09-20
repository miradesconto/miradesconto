# Manutenção atual dos links

`links-afiliados.json` preserva a procedência dos links oficiais. O cadastro
principal é `dados/catalogo.json`; a coleta não pode alterar os links salvos.
Consulte [o procedimento atual](docs/ESTABILIZACAO.md). Os números e o fluxo
descritos abaixo são históricos.

# Histórico — links de afiliado de 16/09/2026

1.009 links gerados pelo gerador oficial na conta MiraDesconto. Etiqueta: instagram. Os 13 produtos recusados pelo programa estão em afiliados-pendentes.json e não aparecem na vitrine.

Ver oferta e Compartilhar usam affiliateUrl. Nenhum botão substitui um link ausente pelo endereço comum do anúncio. Os 1.022 registros originais continuam em produtos.js, com 1.021 imagens. Preços são os coletados na planilha, não atualizados ao vivo.

links-afiliados.json preserva ID, URL de origem, link curto e link completo emitidos pelo Mercado Livre. atualizar_produtos.py reaplica os links apenas quando ID e URL de origem coincidem. Mantenha esse arquivo e imagens-produtos.json junto do conversor.

A geração do link não garante comissão: a compra precisa cumprir as condições do programa. Hospedagem continua no GitHub Pages, sem serviço pago adicional.
