# Estado da implantação — 09/10/2026

As quatro fases foram adaptadas à main `c5b045819542e4156874b58a74310ef6b2cb75d6`.
As coletas e históricos recentes dessa main permanecem intactos.

## Pronto

- Proxy de preços/SWR; redirects oficiais; histórico remoto; publisher Telegram.
- Workflows com ativação por variáveis, sem credenciais no frontend.
- 113 testes Python, 64 JavaScript e smoke test workerd/SQLite/KV aprovados.
- Conferência do catálogo, saúde do site e evidências de preço aprovada.

A coleta mais recente identificou uma variação de `MLB5649300420`, enquanto seu
link oficial arquivado não fixa uma opção. A geração de destinos agora distingue
configuração declarada/URL da opção apenas observada no cartão. O link oficial é
preservado sem inventar parâmetros. O frontend rejeita preço remoto com variação
diferente da evidência vigente; o Telegram também exige equivalência com o registro.
Não alteramos preços ou datas para forçar validação.

## Pendências reais

1. Acesso autenticado ao painel Cloudflare: o navegador remoto do Work recebeu
   `Unable to sign in` no login Google. A sessão do Chrome local não é compartilhada.
2. Criar namespace KV, preencher binding real, publicar o mesmo Worker e seus secrets.
3. Validar acesso real à API ML antes de ativar consulta de preços.
4. Migrar e conferir históricos reais; só então ativar o gráfico e limpar arquivos.
5. Configurar bot/canal, secrets/variables de Actions, validar `--check` e primeiro
   envio Telegram; só então habilitar a rotina automática.

Não houve deploy Cloudflare, migração real, exclusão de histórico nem envio Telegram.
As configurações do frontend permanecem vazias. Esta branch deve ser integrada
quando a infraestrutura e os passos de ativação estiverem prontos; integrá-la antes
substituiria o gráfico local por um gráfico remoto ainda desativado.

Sequência completa nos guias README.md, FASE-2.md, FASE-3.md e FASE-4.md.
