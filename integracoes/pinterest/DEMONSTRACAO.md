# Roteiro de gravação — acesso Standard

Status: roteiro preparado; vídeo real ainda não gravado. App 1613942, Trial.
Duração sugerida: 2–3 minutos. Gravar a janela do navegador com conteúdo legível, ocultando barra de endereço durante OAuth e desativando notificações. Não mostrar painel de chaves, área de transferência, código, state, tokens, arquivos privados ou cabeçalhos Authorization. Não gravar a entrada da chave.

1. **Apresentação (15 s).** Mostrar miradesconto.com.br e o artigo de monitores. Narração: “O MiraDesconto Publicador é uma ferramenta interna para preparar conteúdo editorial da nossa própria conta. Não conectamos contas de visitantes.”
2. **Conexão oficial (30–60 s).** Preparar a chave antes de gravar. Clicar Continuar para o Pinterest. Mostrar nome do app e permissões na página oficial, sem barra de endereço. O titular concede a autorização. Narração: “O titular autoriza sua conta no Pinterest por OAuth. O site público não coleta senha. Solicitamos leitura de pastas e Pins e criação de Pins.”
3. **Retorno e ação real (30 s).** Mostrar Pinterest conectado. Clicar Consultar pastas pela API e mostrar as pastas retornadas. Narração: “Esta consulta real usa GET /v5/boards. No Windows, os tokens ficam criptografados para o usuário, fora do site.”
4. **Conteúdo preparado (20 s).** Mostrar arte e artigo. Narração: “O Pin editorial compara 120 Hz e 144 Hz, informa links de afiliados e não anuncia preços. Nesta versão, nenhum Pin é enviado automaticamente.”
5. **Encerramento (15 s).** Mostrar política de privacidade e explicar revogação. Narração: “A integração permanece em Trial. Publicação automática depende de Standard e proteção durável contra duplicatas. O titular pode revogar o acesso nas configurações do Pinterest.”

## Se incluir criação de um Pin

Ainda não há comando de envio. Antes: hospedar e validar arte, selecionar pasta real, implementar envio único Trial/Sandbox com registro durável, trava e reconciliação. Confirmar Trial no painel. Mostrar somente ID/resposta saneados e Pin real consultado após criação. Não simular publicação nem usar upload manual no Pinterest como prova de POST /v5/pins.

## Revisar e solicitar

Assistir ao vídeo inteiro. Ele deve mostrar consentimento OAuth e uma ação real da API. Protótipos ou testes simulados não substituem evidência. Se ocorrer erro, resolver e gravar novamente. Não declarar criação de Pin quando houve apenas consulta.

Depois: Meus aplicativos → Atualizar MiraDesconto Publicador. Conferir uso interno e política pública, anexar gravação e submeter. Não submeter sem vídeo real conferido. A aprovação cabe ao Pinterest.

Fonte oficial: https://developers.pinterest.com/docs/key-concepts/access-tiers/
