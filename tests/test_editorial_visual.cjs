'use strict';
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
