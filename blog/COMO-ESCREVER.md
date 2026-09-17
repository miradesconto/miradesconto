# Como escrever no blog

Você edita um arquivo de texto por artigo, direto no GitHub. O site cuida do layout, das imagens e dos links dos produtos.

## Escrever em uma pauta existente

1. Abra a [pasta de artigos](https://github.com/miradesconto/miradesconto/tree/main/_artigos), escolha o produto e clique no lápis para editar. Entre na conta com acesso ao repositório.
2. Escreva abaixo da segunda linha `---`. Preserve o cabeçalho entre essas linhas. O título já aparece automaticamente na página.
3. Ajuste `title` (título), `resumo` e `autor`, mantendo as aspas. Preencha `data` com a data real da publicação no formato `"2026-09-17"`. Ao revisar depois, preencha `atualizado` com a data da revisão.
4. Enquanto escreve, mantenha `status: "rascunho"`. Para mostrar o texto no site, troque para `status: "publicado"`.
5. Clique em **Commit changes**, salve na branch **main** e aguarde a publicação automática. Normalmente leva alguns minutos. Confira o artigo no blog.

[Começar pela Mondial AFON-12L-BG](https://github.com/miradesconto/miradesconto/edit/main/_artigos/mondial-afon-12l-bg.md).

O rascunho mostra no site somente a chamada e um aviso de que o artigo ainda não foi publicado. **O repositório é público:** o arquivo salvo no GitHub pode ser lido mesmo sendo rascunho. Não guarde informações privadas nele.

## Formatar o texto

```markdown
Escreva sua introdução aqui.

## Um subtítulo

Um parágrafo com **um trecho em negrito**.

- Primeiro ponto
- Segundo ponto

[Nome da fonte](https://endereco-da-fonte.com)
```

Identifique fontes e datas de consulta. Separe informações do fabricante, da loja e sua experiência. Só descreva testes próprios quando realizados. Atualize título e resumo quando deixar de ser uma pauta futura.

## Adicionar outro artigo

1. Copie o conteúdo do [modelo](MODELO.md).
2. Na pasta `_artigos`, use **Add file → Create new file** e um nome como `meu-produto.md`, sem espaços ou acentos. O nome define o endereço; evite renomear após divulgar.
3. Cole o modelo e substitua título, resumo e produto. Em `produtos`, use o ID real que aparece no endereço **Ver no catálogo** (`MLB...`). Para comparar dois produtos, use dois IDs reais separados por vírgula dentro dos colchetes.
4. Escolha `categoria`: `reviews`, `comparativos` ou `guias`. `ordem` define a posição (menores primeiro). Use `destaque: true` só no artigo principal e mude o anterior para `false`.
5. Escreva e publique. O card aparece automaticamente; imagens e links vêm do catálogo.

Não precisa editar HTML nem executar programas. Se não aparecer, consulte **Actions** no GitHub: uma execução vermelha pode indicar aspas ou cabeçalho incompleto. Artigos vazios continuam como pautas, mesmo com status publicado.
