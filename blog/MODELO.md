# Modelo de artigo

Copie somente o conteúdo do bloco abaixo para um arquivo novo em `_artigos`. Substitua o ID pelo produto real e escreva abaixo da segunda linha `---`.

```markdown
---
title: "Título do seu artigo"
resumo: "Uma frase curta explicando o que o leitor encontrará."
categoria: "reviews"
produtos: ["MLB3941733035"]
status: "rascunho"
autor: "MiraDesconto"
data: ""
atualizado: ""
ordem: 7
destaque: false
---

<!-- Escreva aqui sua introdução e seus subtítulos. -->
```

Categorias: `reviews`, `comparativos`, `guias`. Para publicar, preencha a data real e mude o status para `publicado` depois de escrever e revisar. [Instruções completas](COMO-ESCREVER.md).

## Estrutura de conversão recomendada (revisão de 10/10/2026)

Para artigos publicados sobre tecnologia, preservar o `permalink` existente e, dentro do corpo editorial, seguir a ordem:

1. **Resposta direta**: para quem o modelo vale a pena em 2026 e principal ressalva.
2. **Preço / momento de compra**: referir-se a valor como atual só quando verificado; diferenciar preço de referência de histórico real.
3. **Ver oferta**: usar a CTA principal **VER OFERTA NA LOJA** apenas quando o link individual e a variante forem verificados. Sem URL válida, não criar CTA comercial.
4. **Prós e contras**: com ressalvas sobre falta de teste prático, quando houver.
5. **Ficha e fontes**: links para páginas oficiais do fabricante; não extrapolar especificações de outras versões.
6. **Veredito**: responder se vale a pena, para qual uso, e em qual condição de preço.
7. **Próximo passo**: CTA final à oferta individual válida, ou link ao catálogo/Radar sem promessa de preço.

Nunca alegar “só hoje”, “estoque acabando”, “menor preço histórico” ou “compra segura” sem prova. Disclose de afiliado já é realizado pelo layout. Não gerar botão novo, nem alterar CSS/estrutura/URLs só por copy. Incluir links contextuais discretos quando o produto do artigo tiver o mesmo ID/variante do Radar; os dados de `page.produtos` devem ser confirmados antes da publicação.
