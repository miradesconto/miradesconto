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
 const ctx={window:{}};
 vm.runInNewContext(fs.readFileSync(path.join(root,'produtos.js'),'utf8'),ctx);
 const data=ctx.window.MIRA_DATA;
 const featured=new Set(config.featuredIds);
 if(featured.size!==config.featuredIds.length || featured.size>12) throw Error('Destaques duplicados ou acima do limite de 12.');
 for(const id of featured) if(!data.products.some(p=>p.id===id&&p.affiliateUrl&&p.imageUrl)) throw Error(`Destaque sem cadastro, link ou imagem: ${id}`);
 const changes=[];
 for(const p of data.products) {
  const next=category(p);
  if(p.category!==next) changes.push({id:p.id,name:p.name,before:p.category,after:next});
  p.category=next;p.categorySource='Organização por tipo de produto; regras e revisões em organizacao-catalogo.json';
  p.featured=featured.has(p.id);
 }
 fs.writeFileSync(path.join(root,'produtos.js'),'// Dados da planilha; organização revisada por tipo de produto.\nwindow.MIRA_DATA = '+JSON.stringify(data)+';\n');
 const byId=new Map(data.products.map(p=>[p.id,p]));
 for(const name of fs.readdirSync(path.join(root,'catalogo')).filter(n=>/^produtos-\d+\.json$/.test(n))) {
  const file=path.join(root,'catalogo',name);
  const batch=JSON.parse(fs.readFileSync(file,'utf8'));
  for(const p of batch){const original=byId.get(p.id);if(!original)throw Error(`Registro divergente: ${p.id}`);p.category=original.category;p.featured=original.featured;}
  fs.writeFileSync(file,JSON.stringify(batch)+'\n');
 }
 const counts=data.products.reduce((a,p)=>(a[p.category]=(a[p.category]||0)+1,a),{});
 const analysis=path.join(root,'analise-dados.json');
 if(fs.existsSync(analysis)) {
  const stats=JSON.parse(fs.readFileSync(analysis,'utf8'));stats.categories=counts;
  fs.writeFileSync(analysis,JSON.stringify(stats,null,2)+'\n');
 }
 console.log(JSON.stringify({changed:changes.length,featured:featured.size,categories:counts}));
 return {changes,products:data.products};
}
module.exports={category,organize};
if(require.main===module) organize();
