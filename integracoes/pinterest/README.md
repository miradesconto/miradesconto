# MiraDesconto Publicador — preparação

App 1613942. Acesso Trial solicitado pelo titular; aprovação ainda não confirmada.
Esta entrega implementa somente geração local de rascunhos editoriais. Não possui
cliente HTTP, OAuth, credenciais ou função de publicação. Não depende da pauta de
ofertas, que exige estoque confirmado. Não exibe preço ou desconto nos rascunhos.

Execute `python integracoes/pinterest/preparar.py`. Abra
`preview/pinterest/revisao.html`; `fila.json` contém os mesmos três rascunhos.
Os artigos devem estar publicados e ter produto conhecido. A referência de imagem
não é uma arte final. As pastas são sugestões, sem IDs inventados. Repetir o
comando gera a mesma fila, sempre sem aprovação. `--published-links arquivo.json`
aceita uma lista de URLs já enviadas para excluí-las; não grava histórico de envios.

O workflow **Pinterest — preparar rascunhos** roda apenas por acionamento manual,
com permissão de leitura e sem segredos. Seu ZIP de rascunhos dura sete dias.
O comando local também funciona sem GitHub Actions, sem serviço pago.

## Depois da aprovação Trial

1. Confirmar o status no painel oficial e configurar o retorno OAuth exato.
2. Implementar autorização OAuth com state e troca de código no ambiente privado;
   nunca colocar o app secret ou tokens no JavaScript do site ou em arquivos públicos.
3. Usar somente permissões de leitura dos próprios Pins/pastas e criação de Pins.
4. Implementar cliente e teste de integração no Trial, que não produz Pins públicos.
5. Criar artes finais, revisar textos e escolher as pastas reais.
6. Implementar histórico de envio durável, bloqueio de concorrência e reconciliação
   de resultados incertos antes de repetir uma chamada. A deduplicação de rascunhos
   desta entrega não substitui isso.
7. Demonstrar OAuth e uso real da API para solicitar Standard; somente depois
   habilitar publicação pública, com aprovação editorial e frequência limitada.

O titular pode revogar o acesso nas configurações de aplicativos conectados do
Pinterest. Ao desconectar, remover as credenciais do ambiente privado e os dados
operacionais que deixarem de ser necessários. Pins já publicados são geridos no
Pinterest; remover a autorização não promete apagá-los.

Referências oficiais:
- https://developer.pinterest.com/docs/getting-started/connect-app/
- https://developer.pinterest.com/docs/key-concepts/access-tiers/
- https://help.pinterest.com/en/article/connect-to-other-apps-with-pinterest
