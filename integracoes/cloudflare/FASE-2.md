# MiraDesconto — Fase 2: compra por `/go/:id`

Esta entrega acrescenta a rota de afiliados ao Worker da Fase 1, aos cards de
`interface.js` e ao carrossel de `carrossel.js`. O histórico e a automação social
ficam para as próximas fases. Não houve deploy na Cloudflare nem publicação no site.

## Comportamento

Com `links-config.js` ativado, o botão de cada produto aponta para
`https://SEU_WORKER/go/MLB...` ou `https://miradesconto.com.br/go/MLB...`.
Após o clique, o Worker procura o anúncio no registro oficial, reconstrói a URL
com seus parâmetros de rastreio e devolve **HTTP 302**. A compra não depende
da API de preços, de tokens OAuth ou do Durable Object.

O destino é montado no servidor com `baseUrl + search + hash`. Os parâmetros
emitidos pelo ML entram nessa montagem sem mudar ordem, encoding ou fragmento.
Não se usa a query do visitante para definir URL, etiqueta ou identificação de afiliado.

| Destinos do catálogo inspecionado | Tratamento |
| --- | --- |
| 66 URLs de produto com rastreio oficial | Preserva `wid`, `matt_tool_id`, `tracking_id` e demais parâmetros, inclusive no fragmento |
| 34 links individuais com referência oficial | Usa a URL completa originalmente gerada, preservando `ref`, `matt_tool`, `matt_word` e demais parâmetros |

Nos links existentes, a ferramenta de afiliado é `29904275`; os links
individuais foram gerados com a etiqueta `instagram`. Nenhum ID foi inventado.
`affiliate-policy.json` valida essa identificação para recusar rastreio de outra
conta nos campos em que o ML a fornece. Destinos com `source=lists` sem esse
campo dependem da proveniência registrada no painel do proprietário.
O ML orienta usar links gerados por suas ferramentas. Acrescentar `tag=...` a
um permalink simples não demonstra atribuição de comissão. Por isso a
implementação mantém o rastreio original em vez de substituir o link oficial
por uma URL sem a referência individual. Para trocar a etiqueta, gere novos
links no portal oficial, atualize o cadastro e redeploye o Worker.

O `/social/...` com `ref` individual é a URL completa registrada pelo gerador
oficial; não usamos um perfil `/social/...` sem referência como fallback.
Os 34 destinos opacos têm proveniência no arquivo oficial por anúncio e
variação. Seu comportamento atual no ML precisa ser conferido no teste real:
os testes locais verificam o 302 e a integridade da URL, não a página final
ou a atribuição de uma venda.

## Arquivos novos e alterados

- `affiliate-destinations.js`: valida registro, anúncio, variação e host; responde 302.
- `affiliate-links.json`: destinos e parâmetros oficiais de cada anúncio publicado.
- `affiliate-policy.json`: identificação de afiliado esperada, conferida na geração e no Worker.
- `build_affiliate_links.py`: gera o registro a partir do cadastro e do arquivo oficial.
- `worker.js`: adiciona `/go/:id` antes da restrição CORS da API; mantém o cache de preços.
- Na raiz: `links-config.js`, `links.js`, ajustes em `interface.js`, `carrossel.js`,
  `analytics.js` e na ordem dos scripts em `index.html`.
- Testes de rotas, links, consentimento e proveniência, além do smoke test no workerd.
- Validação do registro e cache-bust no fluxo existente do catálogo.

O GitHub Pages continua servindo o front-end. O Jekyll já exclui `integracoes`;
os módulos do Worker não são carregados pelo navegador.

## 1. Aplicar no repositório e gerar os registros

Extraia os arquivos sobre a versão com a Fase 1 aplicada. O pacote inclui os
arquivos completos das Fases 1 e 2, um patch acumulado sobre a main inspecionada
e um patch apenas da Fase 2. Escolha uma forma de aplicação. Não aplique o patch
depois de copiar os mesmos arquivos.

Na raiz do projeto:

```bash
python3 integracoes/cloudflare/build_allowlist.py
python3 integracoes/cloudflare/build_affiliate_links.py
python3 integracoes/cloudflare/build_affiliate_links.py --check
node --test integracoes/cloudflare/tests/*.test.js
python3 -m unittest discover -s tests -v
```

O gerador falha se encontrar lista genérica sem destino individual, link
ambíguo, rastreio ausente, host inesperado ou anúncio/variação divergentes.
Campanhas antigas do mesmo anúncio podem existir no arquivo: selecionamos
somente o link que corresponde ao cadastro atual.

## 2. Validar e publicar o Worker

```bash
cd integracoes/cloudflare
npm ci
npm run test:runtime
npx wrangler login
npm run deploy
```

Use o mesmo nome de Worker e o mesmo namespace de preços da Fase 1. Não há
novo binding, migração SQLite ou KV nesta fase. `npm run deploy` verifica o
registro antes de publicar. Regere os dois JSONs na raiz se o catálogo mudou.

O login abre o fluxo oficial da Cloudflare no seu computador. Use a conta do
projeto. O endereço `workers.dev` retornado pelo deploy pode ser usado já no
teste. A rota de compra funciona sem configurar novos segredos. Mantenha a
configuração de autenticação de preços da Fase 1 se essa API estiver ativa.

## 3. Conferir 302 e o destino real

Substitua o host abaixo pela URL retornada pelo deploy:

```bash
curl -I 'https://miradesconto-precos.SEU_SUBDOMINIO.workers.dev/go/MLB4408547152'
curl -I 'https://miradesconto-precos.SEU_SUBDOMINIO.workers.dev/go/MLB3931271317'
curl -I 'https://miradesconto-precos.SEU_SUBDOMINIO.workers.dev/go/MLB0000000000'
```

Os dois primeiros retornam `302`, `Location` oficial e `Cache-Control: no-store`.
O terceiro retorna `404`, sem `Location` nem fallback para lista genérica.
`curl -I` não segue a URL de destino e permite inspecionar o cabeçalho.

Para escolher um exemplo do outro formato, ainda dentro de `integracoes/cloudflare`:

```bash
node --input-type=module -e "import links from './affiliate-links.json' with {type:'json'}; console.log(Object.keys(links).find(id => links[id].kind === 'tracked_product'));"
```

Abra o `/go/ID` correspondente no navegador, incluindo um produto com variação
e um dos 34 links com referência individual. Confirme anúncio, vendedor e
configuração. Confira também no relatório do programa a atribuição dos
cliques/vendas após o prazo de atualização do próprio ML. Um 302 correto não
comprova comissão, e não redirecionamos para outro vendedor se a oferta terminar.

No DevTools, em Network com Preserve log, a navegação deve mostrar:

1. `/go/MLB...` retorna 302.
2. `Location` preserva os parâmetros oficiais do registro.
3. Nenhuma chamada a `api.mercadolibre.com` ocorre por causa do clique no botão.

Se o navegador seguir redirecionamentos internos do ML, o destino deles é
decidido pelo marketplace. Se algum link individual abrir a página errada,
gere novamente o link oficial daquele anúncio antes de ativar o site.

## 4. Ativar os botões

Na raiz, configure **somente** `links-config.js`:

```js
window.MIRA_LINK_CONFIG = Object.freeze({
    goBaseUrl: 'https://miradesconto-precos.SEU_SUBDOMINIO.workers.dev'
});
```

A base deve ser a origem HTTPS, sem `/go`, parâmetros, credenciais ou fragmento.
`precos-config.js` é independente: ativar links não obriga ativar consultas de preço.
Publique os arquivos do front-end pelo fluxo normal do GitHub Pages e teste:

- Botão no card e no carrossel: `href` termina em `/go/MLB...`.
- O ID continua sendo o do mesmo anúncio; alternar slides mantém essa relação.
- Com consentimento de métricas: GA4 recebe `affiliate_click`, `item_id` e posição.
- Sem consentimento: nenhuma métrica é enviada e o link continua funcionando.

O clique usa um link normal: não há navegação automática, pop-up ao carregar
ou `fetch()` para seguir o afiliado. `target="_blank"` continua no botão de compra.

Para teste local, execute `python3 -m http.server 8000` na raiz e
`npx wrangler dev --env local` na pasta do Worker em outro terminal. Durante
o teste, use `goBaseUrl: 'http://localhost:8787'`. Volte para HTTPS antes de publicar.

## 5. Usar `/go` no domínio do site

Este passo é opcional. Uma rota de Worker exige zona ativa na Cloudflare e
DNS do domínio com proxy habilitado. Preserve o destino DNS do GitHub Pages.
Com isso já configurado, habilite as entradas `[[routes]]` comentadas no
`wrangler.toml` para os hosts que o site usa e faça novo deploy:

```toml
[[routes]]
pattern = "https://miradesconto.com.br/go/*"
zone_name = "miradesconto.com.br"

[[routes]]
pattern = "https://www.miradesconto.com.br/go/*"
zone_name = "miradesconto.com.br"
```

Essas rotas interceptam somente `/go/*`. Os demais caminhos continuam sendo
servidos pelo GitHub Pages. Configure então `goBaseUrl: 'https://miradesconto.com.br'`.
A API de preços pode continuar no endereço `workers.dev` configurado na Fase 1.
O GitHub Pages sozinho não executa `/go/:id`; ativar apenas a configuração do
JavaScript antes de configurar a rota produziria um 404.

## Manutenção e reversão

- Depois de alterar anúncios publicados, variações ou links oficiais, regere
  `allowed-items.json` e `affiliate-links.json`, confira e redeploye o Worker.
- Se migrar a conta/ferramenta de afiliado, atualize `affiliate-policy.json`
  junto com os novos links oficiais. Alterar apenas o ID não recria referências válidas.
- ID desconhecido recebe 404; registro inválido recebe 503. Não há lista genérica
  como fallback do Worker. GET e HEAD são aceitos; outros métodos recebem 405.
- Parâmetros recebidos como `utm_source`, `fbclid`, `tag`, `url` ou `next` são
  ignorados. Só o ID da rota seleciona um destino previamente validado.
- Para reverter a ativação no front-end, use `goBaseUrl: ''` e publique novamente.
  Os botões voltam aos links oficiais que o catálogo já tinha.
- A rota centraliza destinos e encurta os links dos botões. O destino final
  continua visível no 302, e os URLs existentes continuam no catálogo/repositório
  público. IDs de afiliado não são credenciais secretas; tokens de API continuam
  exclusivamente nos secrets da Cloudflare.

## Verificação executada em 09/10/2026

- **45 testes JavaScript aprovados**: cache e integração da Fase 1, redirects,
  parâmetros oficiais, IDs/variações, host, identificação de afiliado e analytics.
- **75 testes Python aprovados**, incluindo 7 de proveniência, preservação de
  URLs e recusa de lista genérica, referência ambígua e afiliado divergente.
- **workerd/SQLite real**: 100 destinos retornaram 302 com `Location` idêntico ao
  registro; 50 consultas de preços simultâneas geraram 1 chamada upstream simulada.
  Os redirects não fizeram chamadas upstream.
- **JSDOM**: 13 botões por cenário, cards, troca de slides e evento de clique;
  configuração desativada, somente links ativados e links/preços ativados.
- Cadastro, derivados, qualidade/evidência de preço, artigos, analytics e
  saúde do site passaram nas verificações existentes. O Wrangler fez dry-run.

Nenhum desses testes fez uma compra ou validou a atribuição de comissão.
ML, datas de evidência no DOM e respostas de preço foram controlados nos testes.
A conferência no navegador com o marketplace e o deploy real ainda são etapas
da implantação; as configurações entregues permanecem desativadas.

## Fontes oficiais

- Links gerados pelas ferramentas do programa:
  https://www.mercadolivre.com.br/l/afiliados-direcionamento-de-visitas
- Gerador oficial e Barra de Afiliados:
  https://www.mercadolivre.com.br/l/afiliados-gere-seus-links
- Rotas, zona e DNS com proxy:
  https://developers.cloudflare.com/workers/configuration/routing/routes/

Somente iniciar a Fase 3 após a confirmação **Prossiga**.
