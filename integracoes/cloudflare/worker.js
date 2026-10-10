// Fases 1 a 4: preços com SWR + redirect de afiliados oficiais por anúncio.
import allowedItems from './allowed-items.json' with {type: 'json'};
import {affiliateRedirect} from './affiliate-destinations.js';
import {historyRoute} from './history.js';
export {HistoryWriter} from './history.js';
import {socialRoute} from './social-ledger.js';
export {SocialLedger} from './social-ledger.js';

export const POLICY = Object.freeze({fresh: 600, stale: 300, batch: 20, timeout: 8000});
const API = 'https://api.mercadolibre.com';
const positive = n => typeof n === 'number' && Number.isFinite(n) && n > 0;
const json = (body, status = 200, extra = {}) => new Response(JSON.stringify(body), {
  status, headers: {'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', ...extra}
});

class ApiError extends Error {
  constructor(code, status = 502, retry = 60) {
    super(code); this.code = code; this.status = status; this.retry = retry;
  }
}

function retrySeconds(value, now) {
  const numeric = Number(value);
  const seconds = value && Number.isFinite(numeric) ? numeric : (Date.parse(value) - now) / 1000;
  return Math.max(60, Math.min(3600, Math.ceil(Number.isFinite(seconds) ? seconds : 60)));
}

async function timedFetch(url, init = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), POLICY.timeout);
  try {
    // Workers suporta apenas follow/manual. Recusar redirects antes de seguir com Bearer.
    const response = await fetch(url, {...init, signal: controller.signal, redirect: 'manual'});
    if (response.status >= 300 && response.status < 400)
      throw new ApiError('ML_UNEXPECTED_REDIRECT', 502, 300);
    // Ler o corpo dentro do prazo também: fetch() sozinho termina após os headers.
    const raw = await response.text();
    return {response, raw};
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError('ML_NETWORK_OR_TIMEOUT', 504);
  } finally { clearTimeout(timer); }
}

export function normalizeItem(body, id, checkedAt) {
  if (!body || body.id !== id || body.currency_id !== 'BRL'
      || typeof body.status !== 'string') throw new ApiError('ML_INVALID_ITEM');
  const variationId = allowedItems[id];
  let price = body.price;
  if (variationId !== null) {
    const variation = body.variations?.find(v => String(v.id) === variationId);
    // Não aplicar preço de outra configuração nem inferir desconto da variação.
    if (!variation || !positive(variation.price)) throw new ApiError('ML_VARIATION_UNCONFIRMED');
    price = variation.price;
  }
  const available = body.status !== 'active' || body.available_quantity === 0 ? false : null;
  if (!positive(price) && available !== false) throw new ApiError('ML_INVALID_PRICE');
  price = positive(price) ? Math.round(price * 100) / 100 : null;
  if (price !== null && !positive(price)) throw new ApiError('ML_INVALID_PRICE');
  const oldPrice = variationId === null && positive(body.original_price) && body.original_price > price
    ? Math.round(body.original_price * 100) / 100 : null;
  return {id, itemId: id, variationId, price, oldPrice,
    currency: 'BRL', available, availabilityStatus: available === false ? 'unavailable' : 'unknown',
    checkedAt, method: 'ml-edge-item-v1'};
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    // Navegação por clique também vem de redes sociais; CORS restringe apenas a API.
    if (url.pathname === '/go' || url.pathname.startsWith('/go/')) return affiliateRedirect(request);
    if (url.pathname.startsWith('/api/social/')) return socialRoute(request, env);
    if (url.pathname === '/api/history' || url.pathname.startsWith('/api/history/')) return historyRoute(request, env, ctx);
    const origin = request.headers.get('Origin');
    const origins = String(env.ALLOWED_ORIGINS || '').split(',').map(v => v.trim()).filter(Boolean);
    const cors = {'Vary': 'Origin', 'Access-Control-Expose-Headers': 'X-Mira-Cache, Retry-After'};
    if (origin && !origins.includes(origin)) return json({error: 'ORIGIN_NOT_ALLOWED'}, 403);
    if (origin) cors['Access-Control-Allow-Origin'] = origin;
    if (url.pathname !== '/api/prices' && url.pathname !== '/health') return json({error: 'NOT_FOUND'}, 404, cors);
    if (request.method === 'OPTIONS') return new Response(null, {status: 204, headers: {
      ...cors, 'Access-Control-Allow-Methods': 'GET, OPTIONS', 'Access-Control-Max-Age': '600'
    }});
    if (request.method !== 'GET') return json({error: 'METHOD_NOT_ALLOWED'}, 405, {...cors, Allow: 'GET, OPTIONS'});
    if (url.pathname === '/health') return json({phase: 4, service: 'miradesconto-precos',
      freshSeconds: POLICY.fresh, staleSeconds: POLICY.stale,
      allowedItems: Object.keys(allowedItems).length, coordinatorConfigured: Boolean(env.PRICE_CACHE),
      authMode: env.ML_AUTH_MODE || 'access_token',
      historyConfigured: Boolean(env.HISTORY_KV && env.HISTORY_WRITER)}, 200, cors);

    if ([...url.searchParams.keys()].some(k => k !== 'ids') || url.searchParams.getAll('ids').length !== 1)
      return json({error: 'USE_IDS_ONLY'}, 400, cors);
    const requested = url.searchParams.get('ids').split(',');
    if (!requested.length || requested.length > POLICY.batch
        || requested.some(id => !/^MLB\d{7,14}$/.test(id) || !Object.hasOwn(allowedItems, id)))
      return json({error: 'INVALID_OR_UNREGISTERED_IDS', maxIds: POLICY.batch}, 400, cors);
    if (!env.PRICE_CACHE) return json({error: 'COORDINATOR_NOT_CONFIGURED'}, 503, cors);
    try {
      // A mesma identidade global, independente de região, ordem e lote.
      const stub = env.PRICE_CACHE.get(env.PRICE_CACHE.idFromName('ml-prices-v1'));
      const response = await stub.fetch('https://price-cache.internal/prices', {
        method: 'POST', body: JSON.stringify([...new Set(requested)].sort())
      });
      const headers = new Headers(response.headers);
      for (const [key, value] of Object.entries(cors)) headers.set(key, value);
      return new Response(response.body, {status: response.status, headers});
    } catch { return json({error: 'COORDINATOR_UNAVAILABLE'}, 503, {...cors, 'Retry-After': '60'}); }
  }
};

// HTTP Durable Object: SQLite é escolhido por new_sqlite_classes no Wrangler.
export class PriceCache {
  constructor(state, env) {
    this.state = state; this.env = env;
    this.entries = new Map(); this.errors = new Map(); this.inflight = new Map();
    this.control = null; this.oauth = null; this.authInFlight = null;
    this.ready = state.blockConcurrencyWhile(async () => {
      const stored = await state.storage.list();
      for (const [key, value] of stored) {
        if (key.startsWith('price:')) this.entries.set(key.slice(6), value);
        if (key.startsWith('error:')) this.errors.set(key.slice(6), value);
      }
      this.control = stored.get('control') || null;
      this.oauth = stored.get('oauth') || null;
    });
  }

  async fetch(request) {
    await this.ready;
    const ids = await request.json();
    if (!Array.isArray(ids) || ids.length < 1 || ids.length > POLICY.batch
        || ids.some(id => !Object.hasOwn(allowedItems, id))) return json({error: 'INVALID_IDS'}, 400);
    const now = Date.now();
    // Instalar todas as promises antes do primeiro await: elimina corridas entre lotes sobrepostos.
    const due = ids.filter(id => !this.inflight.has(id) && !this.cooldown(id, now)
      && (!this.entries.has(id) || now - this.entries.get(id).at >= POLICY.fresh * 1000));
    if (due.length) this.startBatch(due);
    const items = await Promise.all(ids.map(async id => {
      let record = this.entries.get(id);
      const age = record ? Math.max(0, (now - record.at) / 1000) : Infinity;
      if (record && age < POLICY.fresh) return this.itemResult(id, record, 'HIT', now);
      if (record && age < POLICY.fresh + POLICY.stale) return this.itemResult(id, record, 'STALE', now);
      if (this.inflight.has(id)) await this.inflight.get(id);
      record = this.entries.get(id);
      if (record && Date.now() - record.at < (POLICY.fresh + POLICY.stale) * 1000)
        return this.itemResult(id, record, age === Infinity ? 'MISS' : 'REVALIDATED', Date.now());
      const error = this.cooldown(id, Date.now()) || this.errors.get(id)
        || {code: 'ML_UNAVAILABLE', status: 503, until: Date.now() + 60000};
      return {id, code: error.status, cache: 'ERROR', error: {
        code: error.code, retryAfterSeconds: Math.max(1, Math.ceil((error.until - Date.now()) / 1000))
      }};
    }));
    const modes = [...new Set(items.map(i => i.cache))];
    return json({items, freshSeconds: POLICY.fresh, staleSeconds: POLICY.stale}, 200,
      {'X-Mira-Cache': modes.length === 1 ? modes[0] : 'MIXED'});
  }

  itemResult(id, record, cache, now) {
    return {id, code: 200, cache, ageSeconds: Math.max(0, Math.floor((now - record.at) / 1000)), data: record.data};
  }

  cooldown(id, now) {
    if (this.control?.until > now) return this.control;
    const error = this.errors.get(id);
    return error?.until > now ? error : null;
  }

  startBatch(ids) {
    const job = Promise.resolve().then(() => this.revalidate(ids));
    const finished = job.catch(() => {
      // Falhas de armazenamento/runtime também têm cooldown em memória; não registrar secrets.
      for (const id of ids) this.errors.set(id, {code: 'CACHE_WRITE_FAILED', status: 503, until: Date.now() + 60000});
    }).finally(() => {
      for (const id of ids) if (this.inflight.get(id) === finished) this.inflight.delete(id);
    });
    for (const id of ids) this.inflight.set(id, finished);
    this.state.waitUntil(finished);
  }

  async rememberError(id, error) {
    const value = {code: error.code, status: error.status, until: Date.now() + error.retry * 1000};
    this.errors.set(id, value);
    await this.state.storage.put('error:' + id, value);
  }

  async revalidate(ids) {
    try {
      const fields = 'id,price,original_price,currency_id,status,available_quantity,variations';
      const path = '/items?ids=' + ids.join(',') + '&attributes=' + fields;
      const response = await this.mlGet(path);
      if (!Array.isArray(response) || response.length !== ids.length) throw new ApiError('ML_INVALID_BATCH');
      // O multiget oficial conserva a ordem; conferir o ID de cada corpo antes de utilizá-lo.
      for (let i = 0; i < ids.length; i++) {
        const id = ids[i], item = response[i];
        try {
          if (item?.code === 429) {
            this.control = {code: 'ML_ITEM_HTTP_429', status: 429, until: Date.now() + 60000};
            await this.state.storage.put('control', this.control);
          }
          if (item?.code !== 200) throw new ApiError('ML_ITEM_HTTP_' + (item?.code || 502),
            [401, 403, 404, 429].includes(item?.code) ? item.code : 502, item?.code === 403 ? 300 : 60);
          const at = Date.now(), data = normalizeItem(item.body, id, new Date(at).toISOString());
          const record = {at, data};
          // Só substituir o último dado válido após concluir a gravação.
          await this.state.storage.put('price:' + id, record);
          this.entries.set(id, record); this.errors.delete(id);
          await this.state.storage.delete('error:' + id);
        } catch (error) {
          await this.rememberError(id, error instanceof ApiError ? error : new ApiError('CACHE_WRITE_FAILED', 503));
        }
      }
    } catch (error) {
      const safe = error instanceof ApiError ? error : new ApiError('ML_UNAVAILABLE', 503);
      if ([401, 403, 429].includes(safe.status)) {
        this.control = {code: safe.code, status: safe.status, until: Date.now() + safe.retry * 1000};
        await this.state.storage.put('control', this.control);
      }
      for (const id of ids) await this.rememberError(id, safe);
    }
    console.log(JSON.stringify({event: 'ml_price_revalidation', count: ids.length,
      failed: ids.filter(id => this.errors.has(id)).length}));
  }

  async mlGet(path) {
    let token = await this.accessToken();
    let result = await timedFetch(API + path, {headers: {Accept: 'application/json', Authorization: 'Bearer ' + token}});
    if (result.response.status === 401 && this.env.ML_AUTH_MODE === 'oauth') {
      // Uma renovação por token, mesmo com duas respostas 401 simultâneas.
      if (this.oauth?.accessToken === token) this.oauth.expiresAt = 0;
      token = await this.accessToken();
      result = await timedFetch(API + path, {headers: {Accept: 'application/json', Authorization: 'Bearer ' + token}});
    }
    if (!result.response.ok) throw new ApiError('ML_HTTP_' + result.response.status,
      [401, 403, 429].includes(result.response.status) ? result.response.status : 502,
      result.response.status === 403 ? 300 : retrySeconds(result.response.headers.get('Retry-After'), Date.now()));
    try { return JSON.parse(result.raw); } catch { throw new ApiError('ML_INVALID_JSON'); }
  }

  async accessToken() {
    if (this.env.ML_AUTH_MODE !== 'oauth') {
      if (!this.env.ML_ACCESS_TOKEN) throw new ApiError('ML_TOKEN_NOT_CONFIGURED', 503, 300);
      return this.env.ML_ACCESS_TOKEN;
    }
    const version = String(this.env.ML_AUTH_SEED_VERSION || '1');
    // Enquanto uma renovação já está em andamento, compartilhar sua promise.
    // O marcador persistente blocked protege reinícios, não deve recusar clientes concorrentes.
    if (this.authInFlight) return this.authInFlight;
    if (this.oauth?.seedVersion === version && this.oauth.blocked) throw new ApiError('ML_OAUTH_REAUTHORIZE', 503, 300);
    if (this.oauth?.seedVersion === version && this.oauth.expiresAt > Date.now() + 60000) return this.oauth.accessToken;
    this.authInFlight = this.refreshOAuth(version).finally(() => {this.authInFlight = null;});
    return this.authInFlight;
  }

  async refreshOAuth(version) {
    const refresh = this.oauth?.seedVersion === version ? this.oauth.refreshToken : this.env.ML_REFRESH_TOKEN;
    if (!refresh || !this.env.ML_CLIENT_ID || !this.env.ML_CLIENT_SECRET)
      throw new ApiError('ML_OAUTH_NOT_CONFIGURED', 503, 300);
    // Refresh é de uso único. Persistir a intenção ANTES de enviar; nunca repetir POST incerto.
    this.oauth = {seedVersion: version, blocked: true};
    await this.state.storage.put('oauth', this.oauth);
    try {
      const {response, raw} = await timedFetch(API + '/oauth/token', {method: 'POST',
        headers: {'Content-Type': 'application/x-www-form-urlencoded', Accept: 'application/json'},
        body: new URLSearchParams({grant_type: 'refresh_token', client_id: this.env.ML_CLIENT_ID,
          client_secret: this.env.ML_CLIENT_SECRET, refresh_token: refresh})});
      if (!response.ok) throw new Error('oauth');
      const data = JSON.parse(raw);
      if (typeof data.access_token !== 'string' || !data.access_token
          || typeof data.refresh_token !== 'string' || !data.refresh_token
          || !positive(data.expires_in)) throw new Error('oauth');
      const updated = {seedVersion: version, blocked: false, accessToken: data.access_token,
        refreshToken: data.refresh_token, expiresAt: Date.now() + data.expires_in * 1000};
      await this.state.storage.put('oauth', updated);
      this.oauth = updated;
      return updated.accessToken;
    } catch { throw new ApiError('ML_OAUTH_REAUTHORIZE', 503, 300); }
  }
}
