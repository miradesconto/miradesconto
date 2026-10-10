// Reconstrói somente parâmetros emitidos pelo ML. Não usa tag/URL do visitante.
import allowed from './allowed-items.json' with {type: 'json'};
import destinations from './affiliate-links.json' with {type: 'json'};
import policy from './affiliate-policy.json' with {type: 'json'};

const hosts = new Set(['www.mercadolivre.com.br', 'mercadolivre.com.br']);
const numeric = value => typeof value === 'string' && /^\d{1,20}$/.test(value);
const values = (url, key) => [...url.searchParams.getAll(key),
  ...new URLSearchParams(url.hash.slice(1)).getAll(key)];

export function affiliateDestination(id, record = destinations[id]) {
  try {
    if (!/^MLB\d{7,14}$/.test(id) || !Object.hasOwn(allowed, id) || !record
        || record.variationId !== allowed[id] || typeof record.baseUrl !== 'string'
        || typeof record.search !== 'string' || typeof record.hash !== 'string'
        || (record.search && !record.search.startsWith('?'))
        || (record.hash && !record.hash.startsWith('#'))) return null;
    const base = new URL(record.baseUrl);
    if (base.search || base.hash || record.baseUrl.includes('?') || record.baseUrl.includes('#')) return null;
    const raw = record.baseUrl + record.search + record.hash;
    if (!/^[\x21-\x7e]+$/.test(raw)) return null;
    const url = new URL(raw);
    if (url.protocol !== 'https:' || url.username || url.password || url.port || !hosts.has(url.hostname)) return null;
    if (record.kind === 'signed_link') {
      const ref = values(url, 'ref'), tool = values(url, 'matt_tool'), word = values(url, 'matt_word');
      return /^\/social\/[A-Za-z0-9_-]+$/.test(url.pathname) && !url.hash
        && ref.length === 1 && ref[0] && tool.length === 1 && numeric(tool[0]) && tool[0] === policy.toolId
        && word.length === 1 && word[0] ? raw : null;
    }
    if (record.kind !== 'tracked_product') return null;
    const itemIds = new Set(), variations = new Set();
    const pathItem = /^\/MLB-(\d{7,14})(?:-|\/|$)/i.exec(url.pathname);
    if (pathItem) itemIds.add('MLB' + pathItem[1]);
    // /p e /up identificam páginas de catálogo; o vendedor vem de wid/item_id.
    if (!pathItem && !/\/(?:p\/MLB|up\/MLBU)\d{7,14}(?:\/|$)/i.test(url.pathname)) return null;
    for (const key of ['wid', 'item_id']) {
      for (const value of values(url, key)) {
        const match = /^MLB-?(\d{7,14})$/i.exec(value);
        if (!match) return null;
        itemIds.add('MLB' + match[1]);
      }
    }
    for (const value of values(url, 'pdp_filters'))
      for (const match of value.matchAll(/(?:^|[|,])item_id:MLB-?(\d{7,14})(?=$|[|,])/gi))
        itemIds.add('MLB' + match[1]);
    for (const key of ['searchVariation', 'variation_id'])
      for (const value of values(url, key)) {
        if (!numeric(value)) return null;
        variations.add(value);
      }
    if (itemIds.size !== 1 || !itemIds.has(id) || variations.size > 1
        || ([...variations][0] ?? null) !== allowed[id]) return null;
    const tool = values(url, 'matt_tool_id'), source = values(url, 'source'), tracking = values(url, 'tracking_id');
    if (tool.length && (tool.length !== 1 || tool[0] !== policy.toolId)) return null;
    const tracked = tool.length === 1 && numeric(tool[0]);
    const officialListProduct = source.length === 1 && source[0] === 'lists' && tracking.length === 1
      && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(tracking[0]);
    return tracked || officialListProduct ? raw : null;
  } catch {return null;}
}

export function affiliateRedirect(request) {
  const url = new URL(request.url);
  const headers = {'Cache-Control': 'no-store', 'CDN-Cache-Control': 'no-store',
    'X-Content-Type-Options': 'nosniff', 'X-Robots-Tag': 'noindex, nofollow',
    'Content-Type': 'text/plain; charset=utf-8'};
  const error = (code, status, extra = {}) => new Response(request.method === 'HEAD' ? null : code,
    {status, headers: {...headers, ...extra}});
  if (!['GET', 'HEAD'].includes(request.method)) return error('METHOD_NOT_ALLOWED', 405, {Allow: 'GET, HEAD'});
  const match = /^\/go\/(MLB\d{7,14})$/.exec(url.pathname);
  if (!match) return error('INVALID_ITEM_ID', 400);
  // Ignorar toda a query de entrada mantém cliques com utm/fbclid funcionais.
  // Tag, url, next e outros parâmetros do visitante jamais são encaminhados.
  const id = match[1];
  if (!Object.hasOwn(allowed, id)) return error('ITEM_NOT_REGISTERED', 404);
  const destination = affiliateDestination(id);
  if (!destination) return error('AFFILIATE_DESTINATION_UNAVAILABLE', 503);
  return new Response(null, {status: 302, headers: {...headers, Location: destination}});
}
