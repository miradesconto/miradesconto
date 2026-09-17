// Sync product names and images for Jekyll; articles remain editable Markdown.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..');
function sync(products){
 const data=Object.fromEntries(products.map(p=>[p.id,{name:p.name,imageUrl:p.imageUrl,available:!!p.affiliateUrl}]));
 fs.mkdirSync(path.join(root,'_data'),{recursive:true});
 fs.writeFileSync(path.join(root,'_data/produtos.json'),JSON.stringify(data,null,2)+'\n');
 return data;
}
module.exports={sync};
if(require.main===module){const ctx={window:{}};vm.runInNewContext(fs.readFileSync(path.join(root,'produtos.js'),'utf8'),ctx);sync(ctx.window.MIRA_DATA.products);console.log('Dados editoriais sincronizados.');}
