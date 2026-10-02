# Cadastro de ofertas por link

Abra https://miradesconto.github.io/miradesconto/admin/.

1. Gere o link oficial na ferramenta de afiliados do Mercado Livre.
2. Cole no painel (até 20 links).
3. Autorize com um token GitHub restrito a este repositório, Actions: leitura e escrita.
4. Clique em Adicionar e acompanhe a execução no GitHub.

O token fica somente na memória da página e é apagado do campo após o envio. A página é pública; a escrita exige autorização, e o workflow aceita apenas o proprietário. É possível usar diretamente o botão Run workflow do GitHub sem token no painel.

Arraste o botão de favoritos para a barra do navegador. O atalho pede o link oficial e abre o painel preenchido. Ele não gera links de afiliado.

O cadastro resolve o destino do link, exige identidade inequívoca do anúncio e metadados oficiais, classifica tech e tenta a API quando os Secrets necessários estiverem disponíveis. Se a API não confirmar, tenta o cartão público exato. Página bloqueada, identificação ambígua ou variação exigem revisão; nenhum preço é inventado. O link enviado é preservado literalmente.

Produtos sem desconto ficam cadastrados fora da vitrine e são consultados novamente pela rotina horária. A rotação semanal do acervo antigo foi desativada. As ofertas já publicadas continuam sendo verificadas. GitHub Actions agenda uma tentativa por hora, sujeito a atrasos do serviço e bloqueios do Mercado Livre.

Não foi realizada validação ponta a ponta com um novo link do proprietário. O painel confirma o envio da solicitação, não o sucesso do cadastro. Consulte o resultado da execução antes de divulgar o produto.
