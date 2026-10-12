# Auditoria editorial do PR #36 — Shopee

Data de referência: 12/10/2026. Fonte primária: CSV `BatchProductLinks20261012172405-a5a7f771925a446a9b03f983b24e9695(1).csv` enviado pelo titular (59 itens). Fonte versionada: `_data/shopee_ofertas.csv` (dez itens selecionados).

## Resultado

- **10/10 produtos:** título, ID, link curto, link do anúncio e preço da seleção batem com o CSV original.
- **4/10 links:** abertos em navegador pelo titular na conversa. As URLs finais exibiram `mmp_pid=an_18326581182` e `utm_medium=affiliates`; o produto correspondente foi confirmado pelo titular.
- **6/10 links:** o usuário relatou que os links estão em ordem, e as páginas Shopee com os IDs exatos foram encontradas. A abertura individual dos encurtadores dos itens 5–10 ainda não foi observada nesta auditoria.
- **10/10 imagens vinculadas:** o CSV original não tinha fotos, mas as galerias das dez páginas oficiais Shopee com o ID exato foram localizadas. `image_url` agora contém a foto do anúncio. O carregamento na prévia visual ainda precisa ser conferido; quatro imagens excederam o tempo limite da consulta automática.
- **0/10 preços em tempo real:** valores são exclusivamente referências do CSV. `in_stock=null` e `price_status=unverified`.
- **Nenhuma publicação:** artigos permanecem `status: "rascunho"` e não são introduzidos na vitrine Mercado Livre.

## Itens para conferência manual

| Nº | Produto | ID Shopee | Link afiliado | Redirecionamento | Imagem exata |
|---:|---|---|---|---|---|
| 1 | Mouse Attack Shark X11 | `48360418130` | [Abrir](https://s.shopee.com.br/W7NNInjzy) | Aberto e confirmado pelo titular | Foto vinculada |
| 2 | Power bank 10.000 mAh | `22499247158` | [Abrir](https://s.shopee.com.br/1BN4AWlCe2) | Aberto e confirmado pelo titular | Sem imagem do anúncio |
| 3 | Kit gamer 7 peças | `19299299965` | [Abrir](https://s.shopee.com.br/5AtCvsVyWw) | Aberto e confirmado pelo titular | Sem imagem do anúncio |
| 4 | Teclado mecânico 60% | `23597970068` | [Abrir](https://s.shopee.com.br/3LRYkVcxFh) | Aberto e confirmado pelo titular | Foto vinculada |
| 5 | Kit teclado e mouse RGB | `19722902525` | [Abrir](https://s.shopee.com.br/BUWygp0fs) | Não confirmado externamente | Sem imagem do anúncio |
| 6 | Suporte de notebook | `11758386385` | [Abrir](https://s.shopee.com.br/4qGMXGXFCq) | Não confirmado externamente | Sem imagem do anúncio |
| 7 | Hub USB-C | `18398124948` | [Abrir](https://s.shopee.com.br/40hFXjaPtl) | Não confirmado externamente | Sem imagem do anúncio |
| 8 | Impressora HP 2975 | `9418376328` | [Abrir](https://s.shopee.com.br/50ZmjZWbrv) | Não confirmado externamente | Sem imagem do anúncio |
| 9 | Mousepad 40×40 | `52606084679` | [Abrir](https://s.shopee.com.br/1B6mNpe0r) | Não confirmado externamente | Sem imagem do anúncio |
| 10 | Ring light 12 polegadas | `4096693174` | [Abrir](https://s.shopee.com.br/9APLhEGkQN) | Não confirmado externamente | Sem imagem do anúncio |

## Critérios para aprovação de cada artigo

1. Abrir o link **do anúncio específico** em aba anônima e confirmar título, vendedor, variante e identificador de produto, preservando `utm_medium=affiliates` e o identificador do titular na URL final.
2. Conferir a imagem **do mesmo anúncio e variante**, não apenas um modelo semelhante. Usar foto autorizada ou mídia disponibilizada para divulgação pela plataforma; obter o URL correto e registrar sua procedência. Verificar carregamento da imagem em desktop/mobile e variante antes da publicação.
3. Verificar especificações com documentação confiável e remover afirmações não comprovadas.
4. Revisar preço final, prazo de entrega e estoque na loja. **Nunca substituir `price_status` por “verified” com base no CSV antigo.**
5. Rodar testes, inspecionar desktop/mobile e aprovar explicitamente a mudança de `status`.

### Segurança operacional

- Não clicar para comprar em testes; apenas abrir o anúncio.
- Ausência de resposta automática da Shopee não implica link quebrado; implica **não verificado**.
- PR #36 é Draft e não deve ser mesclado até completar checagem editorial.
- Não modificar CSS da página principal, `produtos.js`, `dados/catalogo.json`, automações ML, nem fazer publicação automática.

## Galerias do anúncio consultadas em 12/10/2026

As fotos abaixo são as imagens principais das galerias correspondentes ao par de IDs do anúncio Shopee e foram vinculadas ao frontmatter de cada artigo, ao CSV editorial e ao catálogo unificado. Fonte primária das imagens: CDN da Shopee. A página de origem está registrada em `image_source`.

| Item Shopee | Foto da galeria | Origem por ID exato |
|---|---|---|
| `48360418130` | [Abrir foto](https://down-br.img.susercontent.com/file/cn-11134207-820l4-mmh5v8n2m6f4e2) | [Anúncio](https://shopee.com.br/Mouse-Attack-Shark-X11-Bluetooth-para-notebook-sem-fio-com-dock-de-carregamento-magn%C3%A9tico-63-g-ultraleve-22000-DPI-novo-i.1672861664.48360418130) |
| `22499247158` | [Abrir foto](https://down-br.img.susercontent.com/file/sg-11134201-81zvk-mik9ovwbhszk62) | [Anúncio](https://shopee.com.br/Carregador-Port%C3%A1til-Mini-Power-Bank-10000mAh-Com-02-Sa%C3%ADdas-Tipo-C-Lightning-i.408715442.22499247158) |
| `19299299965` | [Abrir foto](https://down-br.img.susercontent.com/file/br-11134207-7r98o-m32g7d6pp4ib32) | [Anúncio](https://shopee.com.br/Kit-Mobilador-Completo-7-Pe%C3%A7as-Teclado-Mouse-Gamer-Rgb-Mouse-Pad-Hub-Tripe-Otg-Micro-e-Tipo-c-i.1273492426.19299299965) |
| `23597970068` | [Abrir foto](https://down-br.img.susercontent.com/file/br-11134207-81zuj-ml3uyw8m0s1u70) | [Anúncio](https://shopee.com.br/Teclado-mec%C3%A2nico-projetado-para-jogadores-switch-azul-60-T61-M8701-M6101-azul-vermelho-LEY-2080-i.1147822326.23597970068) |
| `19722902525` | [Abrir foto](https://down-br.img.susercontent.com/file/sg-11134201-825b0-mspngepe38jl75) | [Anúncio](https://shopee.com.br/Kit-Teclado-Gamer-Semi-Mec%C3%A2nico-Mouse-RGB-LED-Iluminado-Multim%C3%ADdia-USB-i.816803352.19722902525) |
| `11758386385` | [Abrir foto](https://down-br.img.susercontent.com/file/57d33ad946c7deb7db078d85e198a963) | [Anúncio](https://shopee.com.br/Suporte-Para-Notebook-Laptop-Multi-Posi%C3%A7%C3%B5es-%C3%93tima-qualidade-Branco-e-Preto-Dobr%C3%A1vel-i.456820962.11758386385) |
| `18398124948` | [Abrir foto](https://down-br.img.susercontent.com/file/br-11134207-81ztc-mjewkx7069z5f0) | [Anúncio](https://shopee.com.br/Adaptador-Hub-Tipo-C-5em2-6em1-7-Em-1-8em1-HDMI-Micro-Sd-Tf-M1-4k-Usb-3.0.-E-USB-A-4EM1.-Para-computador-todo-tipo-i.1314327488.18398124948) |
| `9418376328` | [Abrir foto](https://down-br.img.susercontent.com/file/br-11134201-23010-7poibhljqemv6c) | [Anúncio](https://shopee.com.br/Impressora-Multifuncional-HP-2874-Bivolt-Wifi-Bluetooth-colorida-fotogr%C3%A1fica-preta-i.329543946.9418376328) |
| `52606084679` | [Abrir foto](https://down-br.img.susercontent.com/file/br-11134207-81ztn-mkl0jgpjbnr623) | [Anúncio](https://shopee.com.br/Mouse-Pad-Gamer-Emborrachado-Tamanho-Especial-40x40cm-Tema-Abstrato-i.1285432434.52606084679) |
| `4096693174` | [Abrir foto](https://down-br.img.susercontent.com/file/br-11134207-7r98o-m7cjobl8ywqy07) | [Anúncio](https://shopee.com.br/Kit-Completo-Ring-Light-Profissional-12-polegadas-30cm-C-Trip%C3%A9-2-10M-i.277539644.4096693174) |

**Limitação:** imagens da CDN Shopee podem mudar ou restringir hotlink. Algumas consultas excederam o tempo limite do buscador de imagens, portanto verificar as dez imagens no navegador antes da publicação. A autorização para utilização foi dada pelo titular do MiraDesconto, mas deve respeitar as condições do programa de afiliados e dos detentores do conteúdo.
