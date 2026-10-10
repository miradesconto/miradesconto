import test from 'node:test';
import assert from 'node:assert/strict';
import {socialRoute} from '../social-ledger.js';
const secret='test-only-social-secret-123456789012345678';
const req=(path='/api/social/claim',body={channel:'a'.repeat(64),fingerprint:'b'.repeat(64)},auth=true)=>new Request('https://worker.test'+path,{method:'POST',headers:{'Content-Type':'application/json',...(auth?{Authorization:'Bearer '+secret}:{})},body:typeof body==='string'?body:JSON.stringify(body)});
test('social: autenticação obrigatória antes do binding',async()=>assert.equal((await socialRoute(req(undefined,undefined,false),{})).status,401));
test('social: binding ausente falha fechado',async()=>assert.equal((await socialRoute(req(),{SOCIAL_WRITE_TOKEN:secret})).status,503));
test('social: JSON, canal e tamanho inválidos não chegam ao objeto',async()=>{
  let calls=0;const env={SOCIAL_WRITE_TOKEN:secret,SOCIAL_LEDGER:{get:()=>{calls++;},idFromName:()=>1}};
  for(const body of ['{',null,{},'x'.repeat(5000)]) assert.ok([400,413].includes((await socialRoute(req(undefined,body),env)).status));
  assert.equal(calls,0);
});
test('social: encaminha somente JSON sem bearer ao objeto privado',async()=>{
  const env={SOCIAL_WRITE_TOKEN:secret,SOCIAL_LEDGER:{idFromName:name=>name,get:name=>({fetch:async(url,opts)=>{
    assert.equal(name,'telegram-v1');assert.equal(url,'https://social.internal/api/social/claim');assert.equal(opts.headers,undefined);
    return Response.json({claimed:true,id:'reservation'});
  }})}};
  assert.equal((await (await socialRoute(req(),env)).json()).claimed,true);
});
