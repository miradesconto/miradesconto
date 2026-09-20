# Cadastro e publicação — primeira etapa

## Fonte principal

`dados/catalogo.json` é o cadastro principal: 675 registros nesta migração e 500
IDs em `publishedIds`, na mesma ordem da vitrine. Todos os campos dos 500 produtos
publicados foram preservados, inclusive preços e links.

- `products`: registros completos, inclusive fora da vitrine; a ordem define a
  prioridade da coleta e não muda quando o ranking de exibição é recalculado.
- `publishedIds`: seleção ordenada da última atualização aceita.
- `metadata`: origem e datas da seleção publicada.
- `featuredPolicy`: `first-12-published`, preservando o comportamento atual.

`links-afiliados.json` preserva a procedência dos links oficiais (1.009 entradas).
Links preenchidos no cadastro precisam coincidir com esse arquivo. A coleta não
o substitui. `integracoes/mercadolivre/catalogo-semente.json` foi mantido como
histórico, mas não é mais lido pela sincronização. Produtos com apenas um link no
arquivo de afiliados não foram transformados em cadastros completos inventados.

Algumas pautas em rascunho referenciam IDs conhecidos apenas pelo arquivo de
afiliados; isso é permitido. Artigos publicados precisam referenciar IDs do
cadastro, mas podem tratar de itens fora da vitrine, como o layout já prevê.

## Gerar e verificar

Requisitos: Python 3.12+ e Node 22+. A rotina pública não instala dependências,
não usa OAuth e não precisa de banco de dados ou servidor.

```sh
python integracoes/catalogo.py check
python -m unittest discover -s tests -v
python integracoes/automacao/site_health.py
node test-catalogo.cjs
node blog/verify.cjs
```

Prévia dos dados, sem mudar a fonte nem o site:

```sh
python integracoes/catalogo.py generate --output preview
```

Depois de uma edição revisada do cadastro:

```sh
python integracoes/catalogo.py generate
python integracoes/catalogo.py check
```

Não edite os derivados `produtos.js`, `catalogo/produtos-*.json` e
`_data/produtos.json` diretamente. A verificação detecta diferenças em todos os
campos e lotes extras. `node blog/build.cjs` chama o mesmo gerador. Em ambientes
sem `python` no PATH, defina `PYTHON` com o caminho do executável para os comandos
Node que geram dados.

## Categorias e destaques

Edite `organizacao-catalogo.json` e execute `node organizar_catalogo.cjs`.
O organizador muda apenas categorias no cadastro e regenera os derivados;
não recalcula preços, links ou imagens. Categorias cadastradas podem conter
decisões editoriais; os testes cobrem exemplos das regras sem exigir reclassificar
retroativamente todo produto.

Os destaques são os primeiros 12 IDs publicados. A antiga lista `featuredIds`
foi removida porque já era contrariada pela sincronização. Alterar essa política
é uma decisão futura. No blog, só artigos publicados contam para o limite de um
destaque; o destaque de um rascunho não concorre com eles.

## Coleta e proteção

`run_sync.py` lê o cadastro principal, mantendo o limite de 500 publicados e o
mínimo de 450. Itens que falham continuam cadastrados e podem voltar à vitrine.
Antes de gravar, o gerador valida IDs, preços finitos, links, imagens, ranking e
seleção. A coleta não pode trocar links afiliados nem imagens.

Cada arquivo é substituído atomicamente; o commit completo após as verificações
é a unidade de publicação. Uma interrupção entre gravações locais exige executar
`generate` a partir do cadastro íntegro e depois `check` antes de publicar.

A sincronização só roda em `main`. Pull requests executam testes sem coleta ou
segredos e constroem uma prévia Jekyll em ZIP, retida por 7 dias como artefato.
Não há deploy no workflow de verificação. Nenhum serviço pago foi acrescentado;
o uso continua sujeito às cotas da conta do GitHub.

O importador antigo exige `--output` em pasta separada. Ele serve para prévia,
não para atualizar o cadastro principal. Isso impede sobrescrever a vitrine sem
imagens ou ignorar a fonte principal. Importação revisada fica para outra entrega.

## Limites conhecidos

Na primeira etapa, a extração por proximidade e a inferência de disponibilidade
permaneceram como limitações. A segunda etapa está descrita em
[COLETA-CONFIAVEL.md](COLETA-CONFIAVEL.md), incluindo mudanças de exibição,
validação e limitações restantes. Nenhuma das etapas habilita Pinterest.

`sync_catalog.py` é a implementação separada da API oficial, agora usando o mesmo
cadastro/gerador. Ela exige `cryptography` e credenciais quando executada. Seu
`--dry-run` pode renovar e persistir OAuth; não o use como teste sem efeitos.
Os testes desta etapa não fazem essas chamadas.

## Revisão e recuperação

Referência anterior: `1339d70de3b77c4a5cc7630b676f0c7f4240f6f9`.
Antes do merge, compare novamente com `main`: o agendamento pode ter atualizado
preços enquanto o PR estava aberto. Se houver dados novos, reconcilie o cadastro
com o novo snapshot, preservando a reserva, e repita os testes. Não escolha uma
cópia antiga para resolver conflitos.

Esta migração deve ter diferença zero nos arquivos públicos abaixo:

```sh
git diff 1339d70de3b77c4a5cc7630b676f0c7f4240f6f9 -- produtos.js catalogo _data/produtos.json index.html interface.js _layouts _includes _artigos
```

Para desfazer após merge, reverta o commit de merge em uma nova branch e valide
antes de publicar. Se ocorreram novas coletas, preserve os dados mais recentes;
não restaure o snapshot antigo por cima deles. O histórico guarda a referência.
