// Smoke test no workerd com SQLite real; tráfego ao ML completamente simulado.
import {Miniflare, convertV4MiniflareOptions} from 'miniflare';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import allowed from '../allowed-items.json' with {type: 'json'};
import destinations from '../affiliate-links.json' with {type: 'json'};

const id = Object.keys(allowed).find(key => allowed[key] === null);
let calls = 0;
const runtime = new Miniflare(convertV4MiniflareOptions({
  modules: true, scriptPath: fileURLToPath(new URL('../build-check/worker.js', import.meta.url)),
  compatibilityDate: '2026-10-01',
  durableObjects: {PRICE_CACHE: {className: 'PriceCache', useSQLite: true},
    HISTORY_WRITER: {className:'HistoryWriter',useSQLite:true},
    SOCIAL_LEDGER:{className:'SocialLedger',useSQLite:true}},
  kvNamespaces: ['HISTORY_KV'],
  bindings: {ALLOWED_ORIGINS: 'https://miradesconto.com.br',
    ML_ACCESS_TOKEN: 'runtime-test-token', ML_AUTH_MODE: 'access_token',
    SOCIAL_WRITE_TOKEN:'runtime-only-not-a-real-secret-123456789',
    HISTORY_WRITE_TOKEN:'runtime-only-not-a-real-secret-123456789', HISTORY_DAILY_KV_BUDGET:'2'},
  outboundService: async request => {
    calls++;
    const url = new URL(request.url);
    assert.equal(url.host, 'api.mercadolibre.com');
    assert.equal(request.headers.get('Authorization'), 'Bearer runtime-test-token');
    return Response.json(url.searchParams.get('ids').split(',').map(itemId => ({code: 200, body: {
      id: itemId, price: 123.45, original_price: 199, currency_id: 'BRL', status: 'active', available_quantity: 8
    }})));
  }
}));

try {
  const url = 'https://worker.test/api/prices?ids=' + id;
  const responses = await Promise.all(Array.from({length: 50}, () =>
    runtime.dispatchFetch(url, {headers: {Origin: 'https://miradesconto.com.br'}})));
  const bodies = await Promise.all(responses.map(response => response.json()));
  assert.equal(calls, 1);
  assert.ok(bodies.every(result => result.items[0].code === 200 && result.items[0].data.price === 123.45));
  const hit = await runtime.dispatchFetch(url);
  assert.equal(hit.headers.get('X-Mira-Cache'), 'HIT');
  assert.equal(calls, 1);
  // Todos os destinos no runtime real; redirect manual impede cliques reais no ML.
  for (const [key, value] of Object.entries(destinations)) {
    const redirect = await runtime.dispatchFetch('https://worker.test/go/' + key, {redirect: 'manual'});
    assert.equal(redirect.status, 302, key);
    assert.equal(redirect.headers.get('Location'), value.baseUrl + value.search + value.hash);
  }
  const head = await runtime.dispatchFetch('https://worker.test/go/' + id, {method: 'HEAD', redirect: 'manual'});
  assert.equal(head.status, 302);
  assert.equal(await head.text(), '');
  assert.equal(calls, 1, '/go não consulta API de preços nem segue URLs do ML');
  const socialHeaders={'Content-Type':'application/json',Authorization:'Bearer runtime-only-not-a-real-secret-123456789'};
  const channel='a'.repeat(64),fingerprint='b'.repeat(64);
  const social=async(action,body,headers=socialHeaders)=> {
    const response=await runtime.dispatchFetch('https://worker.test/api/social/'+action,{method:'POST',headers,body:JSON.stringify(body)});
    return {status:response.status,body:await response.json()};
  };
  assert.equal((await social('claim',{channel,fingerprint},{})).status,401);
  const claims=await Promise.all(Array.from({length:20},()=>social('claim',{channel,fingerprint})));
  assert.equal(claims.filter(r=>r.body.claimed).length,1,'uma única reserva global antes do Telegram');
  const reservation=claims.find(r=>r.body.claimed).body.id;
  assert.ok(claims.filter(r=>!r.body.claimed).every(r=>r.body.reason==='needs_reconciliation'));
  assert.equal((await social('finish',{channel,id:reservation,status:'uncertain'})).status,200);
  assert.equal((await social('claim',{channel,fingerprint})).body.reason,'needs_reconciliation');
  assert.equal((await social('finish',{channel,id:reservation,status:'sent',messageId:88})).status,200);
  assert.equal((await social('finish',{channel,id:reservation,status:'sent',messageId:88})).status,200);
  assert.equal((await social('finish',{channel,id:reservation,status:'rejected'})).status,409);
  assert.equal((await social('claim',{channel,fingerprint})).body.reason,'daily_limit');
  const ledger=(await social('status',{channel})).body.records;
  assert.equal(ledger[0].status,'sent');assert.equal(ledger[0].message_id,88);
  assert.equal(calls,1,'ledger não chama Telegram nem ML');
  const historyHeaders = {'Content-Type':'application/json',Authorization:'Bearer runtime-only-not-a-real-secret-123456789'};
  const at = new Date(Date.now()-10000).toISOString();
  const row = {at,price:100,reference:150,itemId:id,variationId:null,method:'poly-card-v1'};
  const ingest = (key,rows,mode='normal') => runtime.dispatchFetch('https://worker.test/api/history/ingest',
    {method:'POST',headers:historyHeaders,body:JSON.stringify({productId:key,currency:'BRL',observations:rows,mode})});
  const historyResults = await Promise.all(Array.from({length:20},async()=> {
    const response = await ingest(id,[row]); assert.equal(response.status,200); return response.json();
  }));
  assert.ok(historyResults.every(value=>value.saved && value.kvPublished && value.revision===1));
  const kv = await runtime.getKVNamespace('HISTORY_KV');
  assert.equal(JSON.parse(await kv.get('history:'+id)).observations.length,1);
  const conflict = await ingest(id,[{...row,at:new Date(Date.now()-20000).toISOString(),price:80},{...row,price:999}]);
  assert.equal(conflict.status,409);
  assert.equal(JSON.parse(await kv.get('history:'+id)).observations[0].price,100);
  const secondRow={...row,at:new Date(Date.now()-5000).toISOString(),price:90};
  const queued=await (await ingest(id,[secondRow])).json();
  assert.equal(queued.saved,true); assert.equal(queued.kvPublished,false);
  assert.ok(['interval','key_rate_limit'].includes(queued.reason));
  // Finalizar migração depois do limite de 1 escrita/chave/segundo.
  await new Promise(resolve=>setTimeout(resolve,1100));
  const flushed=await (await ingest(id,[],'migration')).json();
  assert.equal(flushed.kvPublished,true);
  const stored=JSON.parse(await kv.get('history:'+id));
  assert.equal(stored.observations.length,2);
  const nextId=Object.keys(allowed).find(key=>key!==id && allowed[key]===null);
  const budgeted=await (await ingest(nextId,[{...row,itemId:nextId}])).json();
  assert.equal(budgeted.saved,true); assert.equal(budgeted.kvPublished,false); assert.equal(budgeted.reason,'daily_budget');
  const publicHistory=await runtime.dispatchFetch('https://worker.test/api/history/'+id,
    {headers:{Origin:'https://miradesconto.com.br'}});
  assert.equal(publicHistory.status,200);
  assert.equal((await publicHistory.json()).observations.length,2);
  assert.equal(publicHistory.headers.get('Access-Control-Allow-Origin'),'https://miradesconto.com.br');
  assert.equal(calls,1,'histórico não faz chamadas ao ML');
  console.log(JSON.stringify({runtime: 'workerd/SQLite', social:{concurrentClaims:20,uniqueReservation:1,uncertainBlocked:true,dailyLimit:true}, visitors: 50,
    ML_price_calls: calls, cache: hit.headers.get('X-Mira-Cache'),
    affiliateRedirects: Object.keys(destinations).length,
    history:{concurrentWriters:20,deduplicated:true,conflictRejected:true,rowsAfterFlush:2,dailyBudgetEnforced:true},ok:true}));
} finally {await runtime.dispose();}
