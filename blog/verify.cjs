const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),ctx={window:{}};
vm.runInNewContext(fs.readFileSync(path.join(root,'produtos.js'),'utf8'),ctx);
const data=JSON.parse(fs.readFileSync(path.join(root,'_data/produtos.json'),'utf8'));
const editorialData=JSON.parse(fs.readFileSync(path.join(root,'_data/editorial_products.json'),'utf8'));
const allProducts={...data,...editorialData};
for(const p of ctx.window.MIRA_DATA.products)assert.deepEqual(data[p.id],{name:p.name,imageUrl:p.imageUrl,available:p.available!==false,affiliateUrl:p.offerUrl||p.affiliateUrl});
const registered=new Set(JSON.parse(fs.readFileSync(path.join(root,'dados/catalogo.json'),'utf8')).products.map(p=>p.id));
const archived=new Set(JSON.parse(fs.readFileSync(path.join(root,'links-afiliados.json'),'utf8')).map(p=>p.id));
let count=0,featured=0,missingAffiliate=0,missingImages=0;
const affiliatePattern=/https?:\/\/(?:meli\.la|s\.shopee\.com\.br|amzn\.to|link\.amazon)\//i;

for(const name of fs.readdirSync(path.join(root,'_artigos'))){
 const text=fs.readFileSync(path.join(root,'_artigos',name),'utf8');
 assert.ok(/^---\r?\n/.test(text));
 const m=Object.fromEntries(text.split('---')[1].trim().split('\n').map(line=>{const at=line.indexOf(':');return [line.slice(0,at),JSON.parse(line.slice(at+1).trim())];}));
 assert.ok(['reviews','comparativos','guias'].includes(m.categoria));assert.ok(['rascunho','publicado','arquivado'].includes(m.status));
 assert.ok(m.title&&m.resumo&&Array.isArray(m.produtos));
 for(const id of m.produtos)assert.ok(registered.has(id)||(m.status==='rascunho'&&archived.has(id)),`Produto desconhecido: ${id}`);
 if(m.status==='publicado') {
  const directAffiliate=affiliatePattern.test(text);
  const linkedProducts=m.produtos.filter(id=> {
    const item=allProducts[id];
    return item && /^https:\/\//.test(item.affiliateUrl||'') && /^https:\/\//.test(item.imageUrl||'');
  });
  if(!directAffiliate && linkedProducts.length===0){
    missingAffiliate++;
    console.warn('[MONETIZACAO] Sem link de afiliado publicavel: '+name);
  }
  const hasCover=/^(?:custom_image|image|cover):\s*["']?\S+/m.test(text);
  if(!hasCover && linkedProducts.length===0){
    missingImages++;
    console.warn('[IMAGEM] Revisar imagem editorial: '+name);
  }
}
featured+=(m.status==='publicado'&&m.destaque)?1:0;count++;
}
assert.ok(featured<=1,'Escolha somente um destaque editorial');
console.log(`${count} artigos/pautas válidos; ${Object.keys(data).length} produtos sincronizados.`);

console.log('Auditoria editorial: '+missingAffiliate+' publicados sem afiliado vinculado; '+missingImages+' com imagem a revisar.');
