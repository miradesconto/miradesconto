'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const read = name => fs.readFileSync(path.join(root, name), 'utf8');
const html = read('admin/index.html');
const css = read('admin/painel.css');
const panel = read('admin/painel.js');
const offerPolicy = read('admin/ofertas.js');
const legacy = read('admin/admin.js');

const htmlIds = new Set([...html.matchAll(/\bid="([^"]+)"/g)].map(match => match[1]));
for (const [name, source] of [['painel.js', panel], ['admin.js', legacy]]) {
  for (const match of source.matchAll(/getElementById\('([^']+)'\)/g)) {
    assert.ok(htmlIds.has(match[1]), name + ': elemento #' + match[1] + ' não existe');
  }
}
for (const id of ['form', 'links', 'token', 'submit', 'status', 'bookmark', 'grade',
  'detalhes', 'detalhe-link', 'recarregar', 'busca', 'filtro']) {
  assert.ok(htmlIds.has(id), 'Faltando ID: ' + id);
}
assert.match(html, /content="noindex,nofollow"/);
assert.match(html, /Content-Security-Policy/);
assert.match(html, /href="painel\.css"/);
assert.match(html, /src="painel\.js"/);
assert.match(html, /src="ofertas\.js"/);
assert.match(html, /src="admin\.js"/);
assert.match(css, /\[hidden\]\{display:none!important\}/);
assert.match(panel, /fetch\('\.\.\/dados\/catalogo\.json'/);
assert.match(offerPolicy, /MAX_AGE_MS = 2 \* 60 \* 60 \* 1000/);
assert.match(offerPolicy, /proof\.itemId !== expected/);
assert.match(offerPolicy, /proof\.currency !== 'BRL'/);
assert.match(panel, /validAffiliate\(item\.affiliateUrl\)/);
assert.match(panel, /replaceChildren\(fragment\)/);
assert.match(panel, /fetch\('radar\.json'/);
assert.match(panel, /currentOpportunities/);
assert.match(html, /value="historicas"/);
assert.match(read('admin/radar.json'), /site\.data\.radar \| jsonify/);
assert.ok(!/^\s*- dados\s*$/m.test(read('_config.yml')),
  'Catálogo excluído do Jekyll impede o painel de funcionar');
assert.ok(!/innerHTML\s*=/.test(panel + offerPolicy), 'Não usar innerHTML com dados externos');
assert.ok(!/localStorage|sessionStorage/.test(panel + legacy), 'Não persistir token nem dados privados');
assert.ok(/workflows\/import-affiliate-links\.yml\/dispatches/.test(legacy), 'Preservar fluxo de cadastro existente');
assert.ok(/run-name: Cadastro solicitado/.test(read('.github/workflows/import-affiliate-links.yml')));

const associate = read('admin/associar.js');
for (const match of associate.matchAll(/getElementById\('([^']+)'\)/g)) {
  assert.ok(htmlIds.has(match[1]), 'associar.js: elemento #' + match[1] + ' não existe');
}
for (const id of ['associar-form', 'associar-id', 'associar-url',
  'associar-token', 'associar-status', 'associar-enviar']) {
  assert.ok(htmlIds.has(id), 'Faltando formulário de associação: ' + id);
}
assert.match(html, /src="associar\.js"/);
assert.match(associate, /associate-affiliate-link\.yml\/dispatches/);
assert.match(associate, /product_id: productId/);
assert.match(associate, /affiliate_url: affiliateUrl/);
assert.match(panel, /document\.getElementById\('associar-id'\)\.value = item\.id/);
assert.ok(!/innerHTML\s*=/.test(associate), 'Não usar innerHTML no formulário');
assert.ok(!/localStorage|sessionStorage/.test(associate), 'Não salvar autorização');
const action = read('.github/workflows/associate-affiliate-link.yml');
assert.match(action, /github\.actor == github\.repository_owner/);
assert.match(action, /gh pr create --draft/);
assert.ok(!/git push origin HEAD:main/.test(action), 'Associação não pode publicar diretamente');

console.log('Painel: contratos de DOM, segurança e fluxo de cadastro conferidos.');
