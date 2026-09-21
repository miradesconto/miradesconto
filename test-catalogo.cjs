const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const {category}=require('./organizar_catalogo.cjs');
const ctx={window:{}};vm.runInNewContext(fs.readFileSync(path.join(__dirname,'produtos.js'),'utf8'),ctx);
// Normalize JSON from the VM into this realm before comparing nested evidence.
const products=JSON.parse(JSON.stringify(ctx.window.MIRA_DATA.products));
const config=JSON.parse(fs.readFileSync(path.join(__dirname,'organizacao-catalogo.json')));
const cases=[
 ['Rack para TV 50 polegadas','Casa'],['Criado mudo porta celular','Casa'],
 ['Monitor de pressão arterial digital','Saúde'],['Monitor gamer 24 polegadas','Informática'],
 ['Samsung Galaxy Buds3 fone de ouvido','Eletrônicos'],['Celular Galaxy A17 8GB RAM','Celulares'],
 ['FoxBox Smartwatch Sport','Eletrônicos'],['Gabinete gamer com 4 coolers','Informática'],
 ['Shampoo automotivo Vonixx','Automotivo'],['Shampoo capilar','Beleza e cuidados'],
 ['Cozinha de brinquedo infantil','Brinquedos e bebê'],['Barraca infantil festa do pijama','Brinquedos e bebê'],
 ['Kit ferramentas para manutenção celular notebook','Ferramentas e construção'],
 ['Saia para cama box','Casa'],['Cama box colchão ortopédico','Casa'],
 ['Pistola finca pino com óculos de proteção','Ferramentas e construção'],
 ['Maleta maquiagem com espelho','Beleza e cuidados'],
 ['Produto novo sem descrição suficiente','Outros']
];
for(const [name,expected] of cases) assert.equal(category({name}),expected,name);
assert.equal(new Set(products.map(p=>p.id)).size,products.length);
const selected=products.filter(p=>p.featured);
assert(selected.length>0&&selected.length<=12&&selected.length<products.length);
assert.deepEqual(Array.from(selected,p=>p.id), Array.from(products.slice(0,12),p=>p.id));
assert(selected.every(p=>p.affiliateUrl&&p.imageUrl));
for(const p of products){assert.ok(typeof p.category==='string' && p.category.length,p.id);assert.equal(typeof p.featured,'boolean');}
const chunks=fs.readdirSync(path.join(__dirname,'catalogo')).filter(f=>/^produtos-\d+\.json$/.test(f)).flatMap(f=>JSON.parse(fs.readFileSync(path.join(__dirname,'catalogo',f))));
assert.equal(chunks.length,products.length);
const byId=new Map(products.map(p=>[p.id,p]));
for(const p of chunks) for(const key of Object.keys(p)) assert.deepEqual(p[key],byId.get(p.id)[key],`${p.id}: ${key}`);
console.log(`OK: ${cases.length} regressões de classificação; ${products.length} produtos sincronizados; ${selected.length} destaques pela ordem publicada.`);
