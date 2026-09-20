// All public files share one generator; this command never reads produtos.js.
const path=require('node:path');
function sync() {
 const result=require('node:child_process').spawnSync(process.env.PYTHON || 'python',
  [path.resolve(__dirname,'../integracoes/catalogo.py'),'generate'], {stdio:'inherit'});
 if(result.error) throw result.error;
 if(result.status!==0) throw Error('Falha ao gerar catálogo e dados editoriais');
}
module.exports={sync};
if(require.main===module) sync();
