/* Links cadastrados pelo proprietário; o domínio não comprova a titularidade. */
'use strict';
(function(root) {
  const lists = new Set(['https://meli.la/1NguveN','https://meli.la/1pyBZm8']);
  function platform(value) {
    try {
      const u = new URL(value);
      if (u.protocol !== 'https:' || u.username || u.password || u.port) return null;
      if (u.hostname === 'meli.la' && /^\/[A-Za-z0-9]+\/?$/.test(u.pathname) && !lists.has(value)) return 'mercadolivre';
      if (['amzn.to','a.co'].includes(u.hostname) && /^\/[A-Za-z0-9]+\/?$/.test(u.pathname)) return 'amazon';
      if (['amazon.com.br','www.amazon.com.br'].includes(u.hostname) && u.searchParams.get('tag') && /\/(?:dp|gp\/product)\/[A-Z0-9]{10}(?:\/|$)/i.test(u.pathname)) return 'amazon';
      if (['s.shopee.com.br','shope.ee'].includes(u.hostname) && /^\/[A-Za-z0-9]+\/?$/.test(u.pathname)) return 'shopee';
      return null;
    } catch { return null; }
  }
  function individual(p) {
    const store = platform(p?.affiliateUrl);
    return !!store && p.available !== false && p.affiliateLinkType !== 'list'
      && (store === 'mercadolivre' || (p.affiliateVerified === true && p.affiliateLinkType === 'product'));
  }
  function merge(products) {
    return [...new Map([...(products || []),...(root.MIRA_EXTRA_PRODUCTS || [])].map(p=>[p.id,p])).values()];
  }
  const api={platform,individual,merge};root.MiraAffiliate=api;
  if (typeof module !== 'undefined') module.exports=api;
})(typeof window !== 'undefined' ? window : globalThis);
