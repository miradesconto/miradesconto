// Migração completa no workerd/SQLite/KV local. Não publica nem remove a fonte.
import {Miniflare,convertV4MiniflareOptions} from 'miniflare';
import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';
import {normalizeHistory} from '../history.js';

const folder=new URL('../../../historico/',import.meta.url);
const files=fs.existsSync(folder)?fs.readdirSync(folder).filter(name=>name.endsWith('.json')):[];
const token='local-migration-test-only-not-a-real-secret';
const runtime=new Miniflare(convertV4MiniflareOptions({modules:true,
  scriptPath:fileURLToPath(new URL('../build-check/worker.js',import.meta.url)),compatibilityDate:'2026-10-01',
  durableObjects:{HISTORY_WRITER:{className:'HistoryWriter',useSQLite:true},PRICE_CACHE:{className:'PriceCache',useSQLite:true}},
  kvNamespaces:['HISTORY_KV'],bindings:{HISTORY_WRITE_TOKEN:token},
  outboundService:()=>{throw Error('Migração não deve fazer tráfego externo');}}));
let observations=0,posts=0;
const before=new Map();
try {
  const kv=await runtime.getKVNamespace('HISTORY_KV');
  for(const name of files){
    const path=new URL(name,folder),raw=fs.readFileSync(path,'utf8');before.set(name,raw);
    const expected=normalizeHistory(JSON.parse(raw));
    async function post(rows,mode){
      const response=await runtime.dispatchFetch('https://worker.test/api/history/ingest',{
        method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+token},
        body:JSON.stringify({...expected,observations:rows,mode})});
      assert.ok([200,202].includes(response.status),name+': HTTP '+response.status);
      const result=await response.json();assert.equal(result.saved,true,name);posts++;return result;
    }
    for(let i=0;i<expected.observations.length;i+=64)await post(expected.observations.slice(i,i+64),'stage');
    const published=await post([],'migration');assert.equal(published.kvPublished,true,name);
    const stored=JSON.parse(await kv.get('history:'+expected.productId));
    assert.deepEqual(stored.observations,expected.observations,name);
    observations+=stored.observations.length;
  }
  for(const [name,raw] of before)assert.equal(fs.readFileSync(new URL(name,folder),'utf8'),raw,name);
  console.log(JSON.stringify({runtime:'workerd/SQLite/KV local',files:files.length,observations,posts,
    sourceUnchanged:true,externalRequests:0,ok:true}));
} finally {await runtime.dispose();}
