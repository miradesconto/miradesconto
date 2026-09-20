// Reclassify without rebuilding prices, links, images or source evidence.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = __dirname;
const config = JSON.parse(fs.readFileSync(path.join(root,'organizacao-catalogo.json'),'utf8'));
const normalize = s => s.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
function category(p) {
 if(config.overrides[p.id]) return config.overrides[p.id];
 const name=normalize(p.name);
 return config.rules.find(rule=>new RegExp(rule.pattern).test(name))?.category || 'Outros';
}
function organize() {
 const catalog = JSON.parse(fs.readFileSync(path.join(root,'dados/catalogo.json'),'utf8'));
 const categories = Object.fromEntries(catalog.products.map(p=>[p.id,category(p)]));
 const result = require('node:child_process').spawnSync(process.env.PYTHON || 'python',
  [path.join(root,'integracoes/catalogo.py'),'organize'],
  {input:JSON.stringify(categories),encoding:'utf8'});
 if(result.error) throw result.error;
 if(result.status!==0) throw Error(result.stderr || result.stdout);
 console.log('Categorias atualizadas no cadastro principal; derivados regenerados.');
}
module.exports={category,organize};
if(require.main===module) organize();
