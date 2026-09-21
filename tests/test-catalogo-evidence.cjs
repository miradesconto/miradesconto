const fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {spawnSync}=require('node:child_process');
const assert=require('node:assert/strict'),vm=require('node:vm');
const root=path.resolve(__dirname,'..');
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'mira-evidence-'));
try {
 for(const file of ['test-catalogo.cjs','organizar_catalogo.cjs','organizacao-catalogo.json']) fs.copyFileSync(path.join(root,file),path.join(temp,file));
 const ctx={window:{}};vm.runInNewContext(fs.readFileSync(path.join(root,'produtos.js'),'utf8'),ctx);
 const data=JSON.parse(JSON.stringify(ctx.window.MIRA_DATA));
 data.products[0].priceCheck={status:'verified',price:data.products[0].price,checkedAt:'2026-09-20T18:00:00-03:00'};
 fs.writeFileSync(path.join(temp,'produtos.js'),'window.MIRA_DATA='+JSON.stringify(data)+';');
 fs.mkdirSync(path.join(temp,'catalogo'));
 const chunk=path.join(temp,'catalogo','produtos-1.json');
 fs.writeFileSync(chunk,JSON.stringify(data.products));
 const run=()=>spawnSync(process.execPath,[path.join(temp,'test-catalogo.cjs')],{encoding:'utf8'});
 let result=run();assert.equal(result.status,0,result.stderr);
 data.products[0].priceCheck.price+=1;
 fs.writeFileSync(chunk,JSON.stringify(data.products));
 result=run();assert.notEqual(result.status,0);assert.match(result.stderr,/priceCheck/);
 console.log('OK: evidência aninhada equivalente passa; divergência de valor é bloqueada.');
} finally {fs.rmSync(temp,{recursive:true,force:true});}
