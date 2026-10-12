# Auditoria editorial do PR #36 — Shopee

Data de referência: 12/10/2026. Fonte primária: CSV `BatchProductLinks20261012172405-a5a7f771925a446a9b03f983b24e9695(1).csv` enviado pelo titular (59 itens). Fonte versionada: `_data/shopee_ofertas.csv` (dez itens selecionados).

## Resultado

- **10/10 produtos:** título, ID, link curto, link do anúncio e preço da seleção batem com o CSV original.
- **3/10 links:** abertos em navegador pelo titular na conversa. As URLs finais exibiram `mmp_pid=an_18326581182` e `utm_medium=affiliates`; o produto correspondente foi confirmado pelo titular.
- **7/10 links:** formato correto e presentes na exportação, mas o destino não pôde ser verificado por esta auditoria. Tentativas automatizadas de abrir os encurtadores ou anúncios diretos Shopee foram bloqueadas; não atribuir status “validado”.
- **0/10 imagens:** o CSV original não contém URL de imagem. `image_url` permanece `null`. Pesquisas de fotografias de outros anúncios **não autorizam** associá-las ao anúncio exato.
- **0/10 preços em tempo real:** valores são exclusivamente referências do CSV. `in_stock=null` e `price_status=unverified`.
- **Nenhuma publicação:** artigos permanecem `status: "rascunho"` e não são introduzidos na vitrine Mercado Livre.

## Itens para conferência manual

| Nº | Produto | ID Shopee | Link afiliado | Redirecionamento | Imagem exata |
|---:|---|---|---|---|---|
| 1 | Mouse Attack Shark X11 | `48360418130` | [Abrir](https://s.shopee.com.br/W7NNInjzy) | Aberto e confirmado pelo titular | Sem imagem do anúncio |
| 2 | Power bank 10.000 mAh | `22499247158` | [Abrir](https://s.shopee.com.br/1BN4AWlCe2) | Aberto e confirmado pelo titular | Sem imagem do anúncio |
| 3 | Kit gamer 7 peças | `19299299965` | [Abrir](https://s.shopee.com.br/5AtCvsVyWw) | Aberto e confirmado pelo titular | Sem imagem do anúncio |
| 4 | Teclado mecânico 60% | `23597970068` | [Abrir](https://s.shopee.com.br/3LRYkVcxFh) | Não confirmado externamente | Sem imagem do anúncio |
| 5 | Kit teclado e mouse RGB | `19722902525` | [Abrir](https://s.shopee.com.br/BUWygp0fs) | Não confirmado externamente | Sem imagem do anúncio |
| 6 | Suporte de notebook | `11758386385` | [Abrir](https://s.shopee.com.br/4qGMXGXFCq) | Não confirmado externamente | Sem imagem do anúncio |
| 7 | Hub USB-C | `18398124948` | [Abrir](https://s.shopee.com.br/40hFXjaPtl) | Não confirmado externamente | Sem imagem do anúncio |
| 8 | Impressora HP 2975 | `9418376328` | [Abrir](https://s.shopee.com.br/50ZmjZWbrv) | Não confirmado externamente | Sem imagem do anúncio |
| 9 | Mousepad 40×40 | `52606084679` | [Abrir](https://s.shopee.com.br/1B6mNpe0r) | Não confirmado externamente | Sem imagem do anúncio |
| 10 | Ring light 12 polegadas | `4096693174` | [Abrir](https://s.shopee.com.br/9APLhEGkQN) | Não confirmado externamente | Sem imagem do anúncio |

## Critérios para aprovação de cada artigo

1. Abrir o link **do anúncio específico** em aba anônima e confirmar título, vendedor, variante e identificador de produto, preservando `utm_medium=affiliates` e o identificador do titular na URL final.
2. Conferir a imagem **do mesmo anúncio e variante**, não apenas um modelo semelhante. Usar foto autorizada ou mídia disponibilizada para divulgação pela plataforma; obter o URL correto e registrar sua procedência. Se não houver imagem comprovada, manter o artigo como rascunho.
3. Verificar especificações com documentação confiável e remover afirmações não comprovadas.
4. Revisar preço final, prazo de entrega e estoque na loja. **Nunca substituir `price_status` por “verified” com base no CSV antigo.**
5. Rodar testes, inspecionar desktop/mobile e aprovar explicitamente a mudança de `status`.

### Segurança operacional

- Não clicar para comprar em testes; apenas abrir o anúncio.
- Ausência de resposta automática da Shopee não implica link quebrado; implica **não verificado**.
- PR #36 é Draft e não deve ser mesclado até completar checagem editorial.
- Não modificar CSS da página principal, `produtos.js`, `dados/catalogo.json`, automações ML, nem fazer publicação automática.
