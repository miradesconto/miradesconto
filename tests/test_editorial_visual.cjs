'use strict';
require('./test-site-ui.cjs');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
const photos=JSON.parse(fs.readFileSync(path.join(root,'_data/editorial_products.json')));
const covers=JSON.parse(fs.readFileSync(path.join(root,'_data/editorial_visuals.json')));
const hooks=new Set();let published=0;
for(const name of fs.readdirSync(path.join(root,'_artigos'))){
  const front=fs.readFileSync(path.join(root,'_artigos',name),'utf8').split('---')[1];
  const ids=JSON.parse(front.match(/^produtos: (.+)$/m)[1]);
  const slug=name.slice(0,-3);
  assert.ok(covers[slug],`Capa ausente: ${slug}`);
  assert.ok(!hooks.has(covers[slug].hook),`Chamada repetida: ${slug}`);
  hooks.add(covers[slug].hook);
  for(const id of ids) assert.ok(photos[id],`Produto editorial ausente: ${id}`);
  if(/^status: "publicado"$/m.test(front)){
    published++;
    for(const id of ids) assert.ok(/^https:\/\//.test(photos[id].imageUrl),`Foto ausente: ${id}`);
  }
}
console.log(`${published} artigos publicados com fotos e capas distintas`);


// Product-specific editorial reviews must use the exact registered affiliate URLs and photos.
for (const [slug, id, link] of [
  ['lg-43lr6700psa-vale-a-pena','MLB6739753074','https://meli.la/1cmZy4H'],
  ['kapbom-ka-8596-vale-a-pena','MLB7477193852','https://meli.la/2QmhPHR'],
  ['jbl-tune-780nc-vale-a-pena','MLB4508706691','https://meli.la/1YVasyD'],
  ['machenike-k500b-b87-switch-red-vale-a-pena','MLB5125769735','https://meli.la/2CRn8K3'],
  ['robo-aspirador-kabum-ksar100pt-vale-a-pena','MLB6215775384','https://meli.la/2ZSDYix'],
  ['qcy-gt-s8-vale-a-pena','MLB5211868675','https://meli.la/2vPrV86'],
  ['fechadura-digital-biometrica-touch-id-como-escolher','MLB5209104787','https://meli.la/1HoTph8'],
]) {
  const article=fs.readFileSync(path.join(root,'_artigos',slug+'.md'),'utf8');
  const front=article.split('---')[1],body=article.split('---').slice(2).join('---');
  assert.match(front,/status: "publicado"/);
  assert.ok(front.includes(id),'Article ID must match published listing');
  assert.ok(body.includes(link),'CTA must use the individual affiliate link');
  assert.ok(body.includes(photos[id].imageUrl),'Real listing image required');
  assert.ok(!/["']@type["']\s*:\s*["']Offer["']|R\\\$\s*\d/.test(body),'No stale price or offers schema in article');
  assert.match(body,/Fontes e método/);
  assert.match(body,/Perguntas/);
  assert.match(body,/rel="sponsored nofollow noopener noreferrer"/);
  assert.ok(covers[slug],'Editorial cover entry is required');
  assert.strictEqual(photos[id].affiliateUrl, link);
}
console.log('OK: sete artigos com SKU, foto cadastrada, CTA exato e método editorial.');
