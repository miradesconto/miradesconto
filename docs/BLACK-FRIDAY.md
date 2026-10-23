# Black Friday e destinos do Pinterest

## Enviar produtos
Para cadastrar, reúna nome/modelo, loja, link individual gerado na sua conta e imagem correta do anúncio. Informe também voltagem, capacidade ou outra variante quando houver. Preço e condição de Pix/cupom ajudam na conferência, mas não são publicados como preço verificado sem evidência aceita pelo sistema.

## O que está pronto
- `/black-friday/`: seleção controlada em `_data/black_friday.json`, sem preço vencido.
- `/oferta/<id>/`: destino permanente e específico para Pins. A URL sobrevive à rotação da home.
- `docs/pinterest-destinos.json`: destinos com UTM e identificação dos produtos; são rascunhos, não Pins publicados. O campo `image` é a foto do anúncio para referência, não uma arte vertical pronta.
- Mercado Livre mantém seu cadastro e coleta existentes. O cadastro adicional em `_data/afiliados_extras.json` admite Amazon e Shopee com links individuais confirmados pelo proprietário. Produtos adicionais não têm preço publicado até existir integração de evidência própria.
- A home e o catálogo completo incluem o cadastro adicional. GA4 reconhece as três lojas, respeitando o consentimento.

## Cadastrar Amazon ou Shopee
Prepare uma lista JSON com `id` (AMZ- ou SHP- seguido de slug minúsculo), `name`, `category`, `store` (Amazon/Shopee), `affiliateUrl`, `productUrl`, `imageUrl`, `affiliateVerified: true` e `affiliateLinkType: "product"`.
Use somente URLs HTTPS. A confirmação significa que o link foi gerado na conta correta e aponta para a variante indicada; não é inferida pelo domínio. Links completos Amazon exigem `tag`; links curtos oficiais são aceitos após confirmação. Não inclua `price`, `oldPrice`, `discount` ou `priceCheck` no cadastro adicional.

1. `python integracoes/cadastrar_extra.py /caminho/produtos.json` valida sem gravar.
2. Reconfira o redirecionamento real, a conta de afiliado e a variante antes de aplicar.
3. `python integracoes/cadastrar_extra.py /caminho/produtos.json --apply` gera catálogo adicional e páginas.
4. Para destacar na campanha, acrescente o ID em `_data/black_friday.json` e rode `python integracoes/campanha.py`.
5. Revise o diff, rode os testes e publique os arquivos juntos.

## Verificação
`python integracoes/campanha.py --check` confere cadastro, páginas e destinos reproduzíveis. O workflow do catálogo faz essa verificação. A sincronização de preços regenera os destinos sem editar o cadastro adicional.

Os cliques `affiliate_click` incluem produto, categoria, host da loja e posição do botão. UTMs medem a chegada pelo Pinterest; vendas e comissões precisam ser confirmadas no painel de cada afiliado. A configuração do GA4 não comprova que os eventos foram recebidos: conferir no DebugView/Tempo real com consentimento ativo.

## Coleta de preços
Em 23/10, a recuperação confirmou preços, mas falhou ao enviar o commit por erro de DNS no GitHub. O push agora faz até três tentativas para falhas temporárias, sem forçar ou sobrepor alterações simultâneas. Agendamentos do GitHub podem atrasar; a regra de expirar preços em duas horas permanece. Repetição não garante disponibilidade da rede.
