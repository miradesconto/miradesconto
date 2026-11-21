# Fiscal Gemini: operação e ativação

O check `Gemini gate` bloqueia somente achados CRÍTICOS em PREÇO, HISTÓRICO,
AFILIADO, SEO e SEGURANÇA. Resposta inválida, secret ausente, API indisponível
ou diff acima de 180 KB resultam em NÃO REVISADO, nunca aprovação silenciosa.
Não altera labels ou Draft. Draft escolhido pelo autor é preservado; todo novo
commit é revisado mesmo em Draft. PRs que já estejam em Draft por um bot antigo
devem ser marcados como prontos manualmente, após os checks.

## Reavaliar e contestar

Um usuário com permissão write, maintain ou admin pode comentar:

```
/gemini-recheck
```

Para liberar um falso positivo ou uma indisponibilidade após revisão humana:

```
/gemini-override SHA_COMPLETO justificativa com pelo menos 10 caracteres
```

Use uma única linha, SHA de 40 caracteres do head atual e justificativa concreta.
O check registra o link do comentário e a liberação vale somente para aquele SHA.
Um novo commit requer nova revisão. Falhas de outros checks não são dispensadas.
Usuários sem permissão e comandos malformados/obsoletos são ignorados.
Também há Actions > Gemini — revisar pull request > Run workflow (branch main)
com número do PR. Uma reavaliação posterior substitui a liberação humana.

## Confiança e limites

- Workflow e script são carregados da main, não do PR. Objetos git do PR são
  lidos como dados, sem checkout, instalação de dependências ou execução.
- Gemini recebe a política da main e o diff via API, sem ferramentas/CLI.
- O parser exige JSON consistente, categoria válida, arquivo alterado e trecho
  de evidência presente no diff. Isso reduz falsos positivos, mas não prova que
  a interpretação do modelo esteja correta; a contestação humana é necessária.
- O check mostra categoria, arquivo e linha. Não publica a resposta bruta,
  justificativa do modelo ou trecho de código, pois podem conter credenciais.
- Nunca trunca um diff silenciosamente. PR grande exige divisão ou revisão humana.
- Serialização e conferência de head/base antes da publicação impedem aprovação
  de uma revisão obsoleta. Uma mudança posterior na main exige atualização da
  branch/reavaliação; configure branches atualizadas antes do merge.
- O workflow usa pull_request_target. Se a política de Actions bloquear esse
  evento, ele precisa ser permitido explicitamente para este workflow confiável.
- GEMINI_MODEL pode ser configurado em Actions variables. O padrão preserva
  gemini-3.5-flash-lite. Modelo inválido/indisponível falha como NÃO REVISADO.
- Falha completa do runner antes da conclusão pode deixar check pendente;
  /gemini-recheck cria uma nova execução no mesmo SHA.

## Ativação depois da integração

Este workflow confiável só usa a implementação nova depois de ela entrar na main.
Os testes do PR validam a implementação sem secrets. Não habilite um check
obrigatório que ainda não teve execução real bem-sucedida.

1. Confirmar testes e actionlint aprovados; integrar os arquivos deste PR.
2. Em um PR pequeno e legítimo, executar /gemini-recheck e confirmar `Gemini gate`.
3. Em PRs descartáveis, verificar bloqueio crítico, correção enviada em Draft,
   falso positivo liberado por mantenedor e rejeição de SHA antigo/usuário sem write.
4. Confirmar execução com o modelo/secret reais e tratamento de indisponibilidade.
5. Em Settings > Rules > Rulesets, proteger main: exigir PR, `validate` e
   `Gemini gate`, branch atualizada e aprovação de CODEOWNERS quando aplicável.
   Não usar `review` como nome obrigatório: é o job, não o check publicado no head.
6. Preservar atualizações horárias por bot: elas hoje escrevem direto na main.
   Antes de proibir pushes diretos, migrar esses jobs para PR ou configurar bypass
   restrito ao bot. Não conceder bypass geral só para contornar o Gemini.

CODEOWNERS sozinho não impõe proteção. O proprietário do repositório pode não
conseguir aprovar o próprio PR: configure aprovador independente ou uma exceção
administrativa explícita, sem criar requisito de aprovação impossível de cumprir.
