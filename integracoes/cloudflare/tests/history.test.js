import test from 'node:test';
import assert from 'node:assert/strict';
import worker from '../worker.js';
import {normalizeHistory,publishDecision,HISTORY_POLICY} from '../history.js';
import fs from 'node:fs';

const NOW=Date.parse('2026-10-10T00:30:00Z');
const id='MLB4408547152';
const row={at:'2026-10-09T20:00:00Z',price:100,reference:150,itemId:id,variationId:null,method:'poly-card-v1'};
const doc=observations=>({schemaVersion:1,productId:id,currency:'BRL',observations});
const token='test-only-long-token-not-a-real-secret-12345';

test('histórico normaliza UTC, deduplica e mantém variações separadas',()=>{
  const data=normalizeHistory(doc([row,row,{...row,variationId:'123'}]),NOW);
  assert.equal(data.observations.length,2);
  assert.equal(data.observations[0].at,'2026-10-09T20:00:00+00:00');
  assert.equal(data.observations[0].price,100);
});

test('retenção de 180 dias remove registros antigos sem re-datar observações',()=>{
  const data=normalizeHistory(doc([row,{...row,at:'2025-01-01T00:00:00Z'}]),NOW);
  assert.equal(data.observations.length,1);assert.equal(data.observations[0].at,'2026-10-09T20:00:00+00:00');
});

test('data impossível/futura, preço, método e variação inválidos são recusados',()=>{
  for(const change of [{at:'2026-02-31T00:00:00Z'},{at:'2026-10-11T00:00:00Z'},
    {at:'2026-10-09'},{price:true},{price:0},{reference:-1},{method:'unknown'},
    {variationId:'blue'},{itemId:'MLB123'}])assert.throws(()=>normalizeHistory(doc([{...row,...change}]),NOW));
});

test('preços conflitantes no mesmo instante não sobrescrevem o histórico',()=>{
  assert.throws(()=>normalizeHistory(doc([row,{...row,price:99}]),NOW),/OBSERVATION_CONFLICT/);
});

test('janela de 4h, 1 escrita por segundo e orçamento protegem a cota gratuita',()=>{
  const at=Math.floor(NOW/HISTORY_POLICY.interval)*HISTORY_POLICY.interval;
  assert.equal(publishDecision({at},NOW,1),'interval');
  assert.equal(publishDecision({at},NOW,1,true),null);
  assert.equal(publishDecision({at:NOW-100},NOW,1,true),'key_rate_limit');
  assert.equal(publishDecision({attemptAt:NOW-100},NOW,1,true),'key_rate_limit');
  assert.equal(publishDecision(null,NOW,900),'daily_budget');
  assert.equal(publishDecision({at:at-HISTORY_POLICY.interval},NOW,1),null);
});

test('upload exige POST, token privado e configuração antes de acessar o coordenador',async()=>{
  const env={HISTORY_WRITE_TOKEN:token};
  const url='https://worker.test/api/history/ingest';
  assert.equal((await worker.fetch(new Request(url),env)).status,405);
  assert.equal((await worker.fetch(new Request(url,{method:'POST'}),env)).status,401);
  assert.equal((await worker.fetch(new Request(url,{method:'POST',headers:{Authorization:'Bearer '+token}}),env)).status,503);
});

test('malformed JSON e IDs desconhecidos não chegam ao writer',async()=>{
  const env={HISTORY_WRITE_TOKEN:token,HISTORY_KV:{},HISTORY_WRITER:{get(){throw Error('Não acessar');}}};
  const headers={Authorization:'Bearer '+token,'Content-Type':'application/json'};
  assert.equal((await worker.fetch(new Request('https://worker.test/api/history/ingest',{method:'POST',headers,body:'{'}),env)).status,400);
  const unknown={...doc([row]),productId:'MLB0000000000'};
  assert.equal((await worker.fetch(new Request('https://worker.test/api/history/ingest',{method:'POST',headers,body:JSON.stringify(unknown)}),env)).status,404);
});

test('GET lê só o KV, confirma identidade e aplica CORS sem expor segredos',async()=>{
  let reads=0;
  const env={ALLOWED_ORIGINS:'https://miradesconto.com.br',HISTORY_WRITE_TOKEN:token,
    HISTORY_KV:{async get(key){reads++;assert.equal(key,'history:'+id);return JSON.stringify(doc([{...row,at:new Date(Date.now()-10000).toISOString()}]));}}};
  const url='https://worker.test/api/history/'+id;
  const response=await worker.fetch(new Request(url,{headers:{Origin:'https://miradesconto.com.br'}}),env);
  assert.equal(response.status,200);assert.equal(response.headers.get('Access-Control-Allow-Origin'),'https://miradesconto.com.br');
  const data=await response.json();assert.equal(data.productId,id);assert.equal(data.observations.length,1);
  assert.ok(!JSON.stringify(data).includes(token));
  assert.equal((await worker.fetch(new Request(url,{headers:{Origin:'https://evil.test'}}),env)).status,403);
  assert.equal(reads,1);
  assert.equal((await worker.fetch(new Request(url+'?verify=1'),env)).status,401);
});

const legacyFolder=new URL('../../../historico/',import.meta.url);
const haveLegacy=fs.existsSync(legacyFolder) && fs.readdirSync(legacyFolder).some(name=>name.endsWith('.json'));
test('todos os arquivos legados são compatíveis sem perda de observações',{skip:!haveLegacy},()=>{
  const root=new URL('../../../historico/',import.meta.url);
  let files=0,rows=0;
  for(const name of fs.readdirSync(root).filter(name=>name.endsWith('.json'))){
    const input=JSON.parse(fs.readFileSync(new URL(name,root),'utf8'));
    const output=normalizeHistory(input,Date.now());
    assert.equal(output.observations.length,input.observations.length,name);
    files++;rows+=output.observations.length;
  }
  assert.ok(files>0);assert.ok(rows>0);
});
