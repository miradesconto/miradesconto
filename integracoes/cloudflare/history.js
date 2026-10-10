import knownIds from './history-items.json' with {type: 'json'};
import published from './allowed-items.json' with {type: 'json'};

const known = new Set(knownIds);
export const HISTORY_POLICY = Object.freeze({days: 180, interval: 14400000, budget: 900,
  maxRows: 10000, maxBody: 2097152});
const methods = new Set(['poly-card-v1', 'ml-sale-price-v1', 'ml-edge-item-v1']);
const idOk = id => typeof id === 'string' && /^MLB\d{7,14}$/.test(id);
const priceOk = n => typeof n === 'number' && Number.isFinite(n) && n > 0;
const json = (data, status = 200, headers = {}) => Response.json(data, {status,
  headers: {'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', ...headers}});
export class HistoryError extends Error {
  constructor(code, status = 400) {super(code); this.status = status;}
}

export function normalizeHistory(input, now = Date.now()) {
  if (input?.mode !== undefined && !['normal','stage','migration'].includes(input.mode)) throw new HistoryError('INVALID_MODE');
  if (!input || (input.schemaVersion !== undefined && input.schemaVersion !== 1) || !idOk(input.productId) || input.currency !== 'BRL'
      || !Array.isArray(input.observations) || input.observations.length > HISTORY_POLICY.maxRows)
    throw new HistoryError('INVALID_HISTORY');
  const rows = new Map();
  for (const row of input.observations) {
    const at = Date.parse(row?.at);
    const parts = typeof row?.at === 'string' && /^(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)/.exec(row.at);
    const calendar = parts && Number(parts[2]) >= 1 && Number(parts[2]) <= 12 && Number(parts[3]) >= 1
      && new Date(Date.UTC(Number(parts[1]), Number(parts[2]) - 1, Number(parts[3]))).getUTCDate() === Number(parts[3])
      && Number(parts[4]) < 24 && Number(parts[5]) < 60 && Number(parts[6]) < 60;
    if (!row || !idOk(row.itemId) || !methods.has(row.method) || !priceOk(row.price)
        || !(row.reference === null || priceOk(row.reference))
        || !(row.variationId === null || (typeof row.variationId === 'string' && /^\d{1,20}$/.test(row.variationId)))
        || typeof row.at !== 'string' || !/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)$/.test(row.at)
        || !calendar || !Number.isFinite(at) || at > now) throw new HistoryError('INVALID_OBSERVATION');
    if (at < now - HISTORY_POLICY.days * 86400000) continue;
    const value = {...row, at: new Date(at).toISOString().slice(0, 19) + '+00:00'};
    const clean = {at: value.at, price: value.price, reference: value.reference,
      itemId: value.itemId, variationId: value.variationId, method: value.method};
    const key = JSON.stringify([clean.at, clean.itemId, clean.variationId]);
    if (rows.has(key) && JSON.stringify(rows.get(key)) !== JSON.stringify(clean))
      throw new HistoryError('OBSERVATION_CONFLICT', 409);
    rows.set(key, clean);
  }
  return {schemaVersion: 1, productId: input.productId, currency: 'BRL',
    observations: [...rows.values()].sort((a,b) => a.at.localeCompare(b.at)
      || a.itemId.localeCompare(b.itemId) || String(a.variationId ?? '').localeCompare(String(b.variationId ?? '')))};
}

export function publishDecision(meta, now, used, migration = false, budget = HISTORY_POLICY.budget) {
  if (used >= budget) return 'daily_budget';
  if (meta && now - Math.max(meta.at || 0, meta.attemptAt || 0) < 1000) return 'key_rate_limit';
  if (!migration && meta && Math.floor(meta.at / HISTORY_POLICY.interval) === Math.floor(now / HISTORY_POLICY.interval))
    return 'interval';
  return null;
}

function authorized(request, env) {
  const secret = env.HISTORY_WRITE_TOKEN;
  const provided = request.headers.get('Authorization') || '';
  if (typeof secret !== 'string' || secret.length < 32 || provided.length !== secret.length + 7) return false;
  const expected = 'Bearer ' + secret;
  let diff = 0;
  for (let i = 0; i < expected.length; i++) diff |= expected.charCodeAt(i) ^ provided.charCodeAt(i);
  return diff === 0;
}

export async function historyRoute(request, env, ctx) {
  const url = new URL(request.url);
  if (url.pathname === '/api/history/ingest') {
    if (request.method !== 'POST') return json({error: 'METHOD_NOT_ALLOWED'}, 405, {Allow: 'POST'});
    if (!authorized(request, env)) return json({error: 'UNAUTHORIZED'}, 401);
    if (!env.HISTORY_KV || !env.HISTORY_WRITER) return json({error: 'HISTORY_NOT_CONFIGURED'}, 503);
    if (url.search || !/^application\/json(?:;|$)/i.test(request.headers.get('Content-Type') || ''))
      return json({error: 'USE_JSON_WITHOUT_QUERY'}, 400);
    const raw = await request.text();
    if (new TextEncoder().encode(raw).length > HISTORY_POLICY.maxBody) return json({error: 'BODY_TOO_LARGE'}, 413);
    try {
      const body = JSON.parse(raw);
      if (!known.has(body.productId)) return json({error: 'ITEM_NOT_REGISTERED'}, 404);
      normalizeHistory(body);
      const stub = env.HISTORY_WRITER.get(env.HISTORY_WRITER.idFromName('price-history-v1'));
      return await stub.fetch('https://history.internal/ingest', {method: 'POST', body: raw});
    } catch (error) {
      return json({error: error instanceof HistoryError ? error.message : 'HISTORY_WRITE_FAILED'},
        error instanceof HistoryError ? error.status : error instanceof SyntaxError ? 400 : 503);
    }
  }
  const origin = request.headers.get('Origin');
  const origins = String(env.ALLOWED_ORIGINS || '').split(',').map(v => v.trim());
  const cors = {'Vary': 'Origin'};
  if (origin && !origins.includes(origin)) return json({error: 'ORIGIN_NOT_ALLOWED'}, 403);
  if (origin) cors['Access-Control-Allow-Origin'] = origin;
  if (request.method === 'OPTIONS') return new Response(null, {status: 204, headers: {
    ...cors, 'Access-Control-Allow-Methods': 'GET, OPTIONS', 'Access-Control-Max-Age': '600'}});
  if (request.method !== 'GET') return json({error: 'METHOD_NOT_ALLOWED'}, 405, {...cors, Allow: 'GET, OPTIONS'});
  const match = /^\/api\/history\/(MLB\d{7,14})$/.exec(url.pathname);
  if (!match || !known.has(match[1])) return json({error: 'ITEM_NOT_REGISTERED'}, 404, cors);
  const verify = url.search === '?verify=1';
  if (url.search && !verify) return json({error: 'INVALID_QUERY'}, 400, cors);
  if (verify && !authorized(request, env)) return json({error: 'UNAUTHORIZED'}, 401, cors);
  if (!env.HISTORY_KV) return json({error: 'HISTORY_NOT_CONFIGURED'}, 503, cors);
  try {
    const cache = !verify && typeof caches !== 'undefined' ? caches.default : null;
    const key = new Request(new URL('/api/history/' + match[1], url.origin).href);
    let response = cache && await cache.match(key);
    if (!response) {
      const raw = await env.HISTORY_KV.get('history:' + match[1], {type: 'text', cacheTtl: 60});
      if (raw === null) return json({error: 'HISTORY_NOT_FOUND'}, 404, cors);
      const value = JSON.parse(raw);
      if (!value || value.schemaVersion !== 1 || value.productId !== match[1] || value.currency !== 'BRL'
          || !Array.isArray(value.observations) || value.observations.length > HISTORY_POLICY.maxRows)
        throw new HistoryError('INVALID_STORED_HISTORY');
      // O escritor já validou os registros; não ordenar/serializar milhares de linhas no GET.
      // Consumidores filtram a janela atual de 180 dias do snapshot publicado.
      response = new Response(raw, {headers: {'Content-Type':'application/json; charset=utf-8',
        'X-Content-Type-Options':'nosniff','Cache-Control':'public, max-age=60, s-maxage=60'}});
      if (cache && ctx?.waitUntil) ctx.waitUntil(cache.put(key, response.clone()));
    }
    const headers = new Headers(response.headers);
    for (const [k,v] of Object.entries(cors)) headers.set(k,v);
    if (verify) headers.set('Cache-Control', 'no-store');
    return new Response(response.body, {status: response.status, headers});
  } catch {return json({error: 'HISTORY_READ_FAILED'}, 503, cors);}
}

// SQLite coordena escritores; KV distribui os snapshots para os leitores públicos.
export class HistoryWriter {
  constructor(state, env) {
    this.state = state; this.env = env; this.sql = state.storage.sql; this.tail = Promise.resolve();
    this.sql.exec(`CREATE TABLE IF NOT EXISTS observations (
      product TEXT NOT NULL, at TEXT NOT NULL, item TEXT NOT NULL, variation TEXT NOT NULL,
      price REAL NOT NULL, reference REAL, method TEXT NOT NULL,
      PRIMARY KEY(product, at, item, variation))`);
    this.sql.exec('CREATE TABLE IF NOT EXISTS publication (product TEXT PRIMARY KEY, at INTEGER, revision INTEGER)');
    this.sql.exec('CREATE TABLE IF NOT EXISTS attempts (product TEXT PRIMARY KEY, at INTEGER)');
    this.sql.exec('CREATE TABLE IF NOT EXISTS revisions (product TEXT PRIMARY KEY, revision INTEGER NOT NULL)');
    this.sql.exec('CREATE TABLE IF NOT EXISTS budgets (day TEXT PRIMARY KEY, used INTEGER NOT NULL)');
  }
  async fetch(request) {
    const raw = await request.text();
    const operation = this.tail.then(() => this.ingest(JSON.parse(raw)));
    this.tail = operation.catch(() => {});
    try {return await operation;}
    catch (error) {return json({error: error instanceof HistoryError ? error.message : 'HISTORY_WRITE_FAILED'},
      error instanceof HistoryError ? error.status : 503);}
  }
  async ingest(input) {
    const now = Date.now(), data = normalizeHistory(input, now), id = data.productId;
    if (!known.has(id)) throw new HistoryError('ITEM_NOT_REGISTERED', 404);
    if (!this.env.HISTORY_KV) throw new HistoryError('HISTORY_NOT_CONFIGURED', 503);
    const cutoff = new Date(now - HISTORY_POLICY.days * 86400000).toISOString().slice(0,19) + '+00:00';
    const revision = this.state.storage.transactionSync(() => {
      let changed = false;
      for (const row of data.observations) {
        const prior = [...this.sql.exec('SELECT price, reference, method FROM observations WHERE product=? AND at=? AND item=? AND variation=?',
          id, row.at, row.itemId, row.variationId ?? '')][0];
        if (prior && (prior.price !== row.price || prior.reference !== row.reference || prior.method !== row.method))
          throw new HistoryError('OBSERVATION_CONFLICT', 409);
        if (!prior) {
          this.sql.exec('INSERT INTO observations VALUES (?,?,?,?,?,?,?)', id, row.at, row.itemId,
            row.variationId ?? '', row.price, row.reference, row.method);
          changed = true;
        }
      }
      const removed = this.sql.exec('DELETE FROM observations WHERE product=? AND at<?', id, cutoff);
      changed ||= removed.rowsWritten > 0;
      const previous = [...this.sql.exec('SELECT revision FROM revisions WHERE product=?',id)][0]?.revision ?? 0;
      const next = previous + Number(changed);
      this.sql.exec('INSERT OR REPLACE INTO revisions VALUES (?,?)',id,next);
      return next;
    });
    const meta = [...this.sql.exec('SELECT at, revision FROM publication WHERE product=?',id)][0];
    const result = {saved: true, productId: id, revision, accepted: data.observations.length};
    if (input.mode === 'stage') return json({...result,kvPublished:false,reason:'staged'},202);
    if (meta?.revision === revision) return json({...result, kvPublished: true, reason: 'unchanged'});
    const migration = input.mode === 'migration';
    if (!migration && !Object.hasOwn(published,id)) return json({...result, kvPublished: false, reason: 'not_published'},202);
    const day = new Date(now).toISOString().slice(0,10);
    const used = [...this.sql.exec('SELECT used FROM budgets WHERE day=?',day)][0]?.used ?? 0;
    const configured = Number(this.env.HISTORY_DAILY_KV_BUDGET || HISTORY_POLICY.budget);
    const budget = Math.max(1, Math.min(HISTORY_POLICY.budget, Number.isFinite(configured) ? configured : HISTORY_POLICY.budget));
    const attemptAt = [...this.sql.exec('SELECT at FROM attempts WHERE product=?',id)][0]?.at;
    const reason = publishDecision({...meta,attemptAt}, now, used, migration, budget);
    if (reason) return json({...result, kvPublished:false, reason},202);
    const rows = [...this.sql.exec('SELECT at, price, reference, item AS itemId, variation AS variationId, method FROM observations WHERE product=? ORDER BY at,item,variation',id)]
      .map(row => ({...row, variationId: row.variationId || null}));
    if (rows.length > HISTORY_POLICY.maxRows) throw new HistoryError('HISTORY_TOO_LARGE',413);
    const document = {schemaVersion:1,productId:id,currency:'BRL',updatedAt:new Date(now).toISOString(),observations:rows};
    // Reservar inclusive tentativas incertas: retries não estouram a cota diária.
    this.sql.exec('INSERT OR REPLACE INTO budgets VALUES (?,?)',day,used+1);
    this.sql.exec('INSERT OR REPLACE INTO attempts VALUES (?,?)',id,now);
    this.sql.exec('DELETE FROM budgets WHERE day<?',day);
    await this.state.storage.sync();
    try {
      await this.env.HISTORY_KV.put('history:' + id, JSON.stringify(document));
    } catch {return json({...result,kvPublished:false,reason:'kv_error'},202);}
    this.sql.exec('INSERT OR REPLACE INTO publication VALUES (?,?,?)',id,now,revision);
    return json({...result,kvPublished:true,reason:'published'});
  }
}
