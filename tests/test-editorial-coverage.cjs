'use strict';
const fs = require('node:fs'), assert = require('node:assert/strict');
const scope = JSON.parse(fs.readFileSync('docs/COBERTURA-EDITORIAL-20261012.json','utf8'));
let count = 0;
for (const [id, record] of Object.entries(scope.products)) {
  const slug = record.article.split('/').filter(Boolean).at(-1);
  const text = fs.readFileSync('_artigos/'+slug+'.md','utf8');
  const parts = text.split('---'); const front=parts[1], body=parts.slice(2).join('---');
  assert.match(front,/^status: "publicado"$/m);
  const ids = JSON.parse(front.match(/^produtos: (.*)$/m)[1]);
  assert(ids.includes(id),id+' sem vínculo no artigo');
  assert(record.analysis.length > 70,id+' sem análise de compra');
  assert.match(body,/Fonte|Método|método|Base da análise|base deste|Como verificamos/i);
  count++;
}
for (const filename of fs.readdirSync('_artigos')) {
  const text = fs.readFileSync('_artigos/'+filename,'utf8');
  if (!text.split('---')[1].includes('status: "publicado"')) continue;
  assert(!/currentPriceText|"@type": "Offer"/.test(text),filename+' com preço estático no texto/schema');
}
console.log('OK: '+count+' anúncios com cobertura publicada, análise de compra e fontes/método; sem preços fixos de Radar no corpo.');
