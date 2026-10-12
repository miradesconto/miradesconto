# Cadastro de ofertas por link

Abra https://miradesconto.com.br/admin/.

1. Gere o link oficial na ferramenta de afiliados do Mercado Livre.
2. Cole no painel (até 20 links).
3. Autorize com um token GitHub restrito a este repositório, Actions: leitura e escrita.
4. Clique em Adicionar e acompanhe a execução no GitHub.

O token fica somente na memória da página e é apagado do campo após o envio. A página é pública; a escrita exige autorização, e o workflow aceita apenas o proprietário. É possível usar diretamente o botão Run workflow do GitHub sem token no painel.

Arraste o botão de favoritos para a barra do navegador. O atalho pede o link oficial e abre o painel preenchido. Ele não gera links de afiliado.

O cadastro resolve o destino do link, exige identidade inequívoca do anúncio e metadados oficiais, classifica tech e tenta a API quando os Secrets necessários estiverem disponíveis. Se a API não confirmar, tenta o cartão público exato. Página bloqueada, identificação ambígua ou variação exigem revisão; nenhum preço é inventado. O link enviado é preservado literalmente.

Produtos sem desconto ficam cadastrados fora da vitrine e são consultados novamente pela rotina horária. A rotação semanal do acervo antigo foi desativada. As ofertas já publicadas continuam sendo verificadas. GitHub Actions agenda uma tentativa por hora, sujeito a atrasos do serviço e bloqueios do Mercado Livre.

Não foi realizada validação ponta a ponta com um novo link do proprietário. O painel confirma o envio da solicitação, não o sucesso do cadastro. Consulte o resultado da execução antes de divulgar o produto.

## Link de produto que abre um perfil público

Alguns links gerados para um anúncio individual abrem a página social do afiliado, com um produto principal e recomendações abaixo. **O cadastro automático nunca deve atribuir o mesmo link às recomendações.**

Para esses casos, depois que o proprietário testar o botão "Ir para produto" e conferir o anúncio exato, o cadastro pode ser solicitado pelo arquivo `integracoes/mercadolivre/cadastro-pendente.json`, com o campo `expectedItemIds` associando o link oficial ao ID `MLB...` confirmado. O importador seleciona exclusivamente o cartão que tiver esse ID, valida o preço do cartão e rejeita a operação se o anúncio não puder ser identificado. O painel de cadastro comum continua recusando perfis sem identificação explícita.

O ID confirmado pelo proprietário não substitui a checagem de preço nem garante comissão. Links de listas identificadas continuam seguindo a rotina própria.

## Listas públicas de afiliado

Apenas links que resolvem para uma **lista explicitamente identificada** (com `/lists/` no destino) podem cadastrar múltiplos anúncios. Links que redirecionam ao **perfil público do afiliado** (`/social/...` sem `/lists/`) exibem recomendações e **não comprovam** que o link de afiliado corresponde a cada anúncio. O cadastro deve rejeitá-los para não atribuir o mesmo link a produtos diferentes. Para um produto individual, gere o link direto do anúncio pela ferramenta oficial de afiliados.

Um link que abre uma lista pode cadastrar todos os cartões tech com anúncio, imagem e preço exatos confirmados. O sistema preserva o link oficial da lista para a compra. Itens não tech, ambíguos ou com variação são ignorados. A lista cadastrada com sucesso fica em metadata.affiliateSources e é consultada pela rotina horária para descobrir novos produtos. Falhas de leitura preservam o catálogo. Retirar um produto da lista ainda não remove seu cadastro automaticamente.
