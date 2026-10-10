// Registro durável de intenção antes de efeitos externos; sem token Telegram aqui.
const reply = (body,status=200) => Response.json(body,{status,headers:{'Cache-Control':'no-store'}});
const hash = value => typeof value==='string' && /^[a-f0-9]{64}$/.test(value);
export async function socialRoute(request,env) {
  const url=new URL(request.url);
  if (!['/api/social/claim','/api/social/finish','/api/social/status'].includes(url.pathname)) return reply({error:'NOT_FOUND'},404);
  if(request.method!=='POST') return reply({error:'METHOD_NOT_ALLOWED'},405);
  const secret=env.SOCIAL_WRITE_TOKEN, provided=request.headers.get('Authorization')||'';
  let diff=0;
  if(typeof secret!=='string'||secret.length<32||provided.length!==secret.length+7) return reply({error:'UNAUTHORIZED'},401);
  const expected='Bearer '+secret;
  for(let i=0;i<expected.length;i++) diff|=expected.charCodeAt(i)^provided.charCodeAt(i);
  if(diff) return reply({error:'UNAUTHORIZED'},401);
  if(!env.SOCIAL_LEDGER) return reply({error:'NOT_CONFIGURED'},503);
  if(url.search||!/^application\/json(?:;|$)/i.test(request.headers.get('Content-Type')||'')) return reply({error:'INVALID_REQUEST'},400);
  const raw=await request.text();
  if(new TextEncoder().encode(raw).length>4096) return reply({error:'BODY_TOO_LARGE'},413);
  let body;
  try {body=JSON.parse(raw);} catch {return reply({error:'INVALID_JSON'},400);}
  try {
    if(!body || !hash(body.channel)) return reply({error:'INVALID_CHANNEL'},400);
    return await env.SOCIAL_LEDGER.get(env.SOCIAL_LEDGER.idFromName('telegram-v1')).fetch('https://social.internal'+url.pathname,{method:'POST',body:raw});
  }catch {return reply({error:'SOCIAL_STATE_FAILURE'},503);}
}
export class SocialLedger {
  constructor(state) {
    this.state=state;this.sql=state.storage.sql;
    this.sql.exec(`CREATE TABLE IF NOT EXISTS sends (id TEXT PRIMARY KEY, channel TEXT, day TEXT,
      fingerprint TEXT, created INTEGER, status TEXT, message_id INTEGER, UNIQUE(channel,day))`);
  }
  async fetch(request) {
    const body=await request.json(), action=new URL(request.url).pathname.split('/').pop();
    if(!hash(body.channel)) return reply({error:'INVALID_CHANNEL'},400);
    const now=Date.now(),day=new Intl.DateTimeFormat('en-CA',{timeZone:'America/Sao_Paulo',year:'numeric',month:'2-digit',day:'2-digit'}).format(now);
    if(action==='status') return reply({records:[...this.sql.exec('SELECT id,day,status,message_id FROM sends WHERE channel=? ORDER BY created DESC LIMIT 20',body.channel)]});
    if(action==='claim') {
      if(!hash(body.fingerprint)) return reply({error:'INVALID_FINGERPRINT'},400);
      const pending=[...this.sql.exec("SELECT id FROM sends WHERE channel=? AND status IN ('reserved','uncertain') LIMIT 1",body.channel)][0];
      if(pending) return reply({claimed:false,reason:'needs_reconciliation',id:pending.id});
      if([...this.sql.exec('SELECT id FROM sends WHERE channel=? AND day=?',body.channel,day)].length) return reply({claimed:false,reason:'daily_limit'});
      if([...this.sql.exec("SELECT id FROM sends WHERE channel=? AND fingerprint=? AND status='sent' AND created>?",body.channel,body.fingerprint,now-72*3600000)].length) return reply({claimed:false,reason:'duplicate_72h'});
      const id=crypto.randomUUID();
      this.sql.exec("INSERT INTO sends VALUES (?,?,?,?,?,'reserved',NULL)",id,body.channel,day,body.fingerprint,now);
      await this.state.storage.sync();
      return reply({claimed:true,id});
    }
    if(action==='finish') {
      if(typeof body.id!=='string'||!['sent','rejected','uncertain'].includes(body.status)
          ||(body.status==='sent'&&(!Number.isSafeInteger(body.messageId)||body.messageId<=0))) return reply({error:'INVALID_RECEIPT'},400);
      const row=[...this.sql.exec('SELECT * FROM sends WHERE id=? AND channel=?',body.id,body.channel)][0];
      if(!row) return reply({error:'NOT_FOUND'},404);
      if(!['reserved','uncertain'].includes(row.status)) {
        return row.status===body.status && (body.status!=='sent'||row.message_id===body.messageId)
          ? reply({saved:true}) : reply({error:'ALREADY_RESOLVED'},409);
      }
      this.sql.exec('UPDATE sends SET status=?,message_id=? WHERE id=?',body.status,body.status==='sent'?body.messageId:null,body.id);
      await this.state.storage.sync();return reply({saved:true});
    }
    return reply({error:'NOT_FOUND'},404);
  }
}
