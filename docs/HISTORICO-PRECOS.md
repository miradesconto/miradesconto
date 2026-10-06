# Histórico de preços

O workflow horário arquiva observações com evidência verificada após a atualização de preços.
Cada anúncio possui um JSON em `historico/`. O navegador carrega somente o anúncio solicitado.
Preços atuais e referência promocional são campos separados; nenhuma referência vira observação histórica.

São aceitos apenas métodos conhecidos, moeda BRL, identidade e valores coerentes e datas com fuso,
sem datas futuras e dentro de 180 dias. Coletas repetidas são deduplicadas por data, anúncio e variação.
A interface separa item e variação e mostra 30, 90 e 180 dias, menor, maior e tabela de observações.
Não declara cobertura completa, menor preço de mercado ou seis meses completos quando faltam registros.
Frete e cupons pessoais não são incluídos. Valores atuais exigem evidência de até 24 horas.

Recuperação inicial: `python integracoes/mercadolivre/price_history.py --backfill`.
O histórico de commits é lido localmente; arquivos recuperados são públicos e não incluem credenciais.
Primeiras observações recuperadas: 21/09/2026. Esse início varia por anúncio e variação.

Teste: `python -m unittest discover -s tests -p test_price_history.py`.
