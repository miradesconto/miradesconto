'use strict';
(() => {
  const id = String(window.MIRA_GA4_ID || '').trim().toUpperCase();
  const configured = /^G-[A-Z0-9]{5,20}$/.test(id);
  // Only aggregate counters in page memory: no cookies, storage or network.
  const counts = new Map();
  const scriptUrl = document.currentScript?.src || new URL('analytics.js', window.location.href).href;
  const key = 'mira_analytics_consent_v1';
  let choice;
  try { choice = configured ? localStorage.getItem(key) : null; } catch { choice = null; }
  let started = false;

  function start() {
    if (!configured) return;
    window['ga-disable-' + id] = false;
    if (started) return;
    started = true;
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag('js', new Date());
    window.gtag('config', id, {send_page_view: true,
      page_location: window.location.origin + window.location.pathname,
      page_referrer: '', allow_google_signals: false, allow_ad_personalization_signals: false});
    const script = document.createElement('script');
    script.async = true;
    script.src = 'https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(id);
    document.head.append(script);
  }

  function isAffiliate(href) {
    try {
      const url = new URL(href, window.location.href);
      return url.protocol === 'https:' && (url.hostname === 'meli.la' ||
        ((url.hostname === 'www.mercadolivre.com.br' || url.hostname === 'mercadolivre.com.br')
          && url.pathname.startsWith('/social/')));
    } catch { return false; }
  }

  function track(event) {
    if (event.type === 'auxclick' && event.button !== 1) return;
    const link = event.target?.closest?.('a[href]');
    if (!link || !isAffiliate(link.href)) return;
    const catalog = window.MIRA_DATA?.products || [];
    const product = catalog.find(p => p.affiliateUrl === link.href);
    const location = link.closest('.hero') ? 'hero' :
      link.closest('#productList') ? 'catalog' : link.closest('article') ? 'article' : 'other';
    const params = {
      link_location: location,
      affiliate_host: new URL(link.href).hostname,
    };
    if (product?.id) params.item_id = product.id;
    if (product?.category) params.item_category = product.category;
    const counterKey = JSON.stringify(params);
    counts.set(counterKey, (counts.get(counterKey) || 0) + 1);
    window.dispatchEvent(new CustomEvent('mira:affiliate_click', {detail: {...params}}));
    if (choice === 'granted' && started) window.gtag('event', 'affiliate_click', params);
  }

  let banner;
  function hideBanner() { banner?.remove(); banner = null; }
  function save(value) {
    choice = value;
    try { localStorage.setItem(key, value); } catch { /* Navegação continua sem armazenamento. */ }
    hideBanner();
    if (value === 'granted') start();
    else window['ga-disable-' + id] = true;
  }
  function showBanner() {
    if (!configured) return;
    if (banner) return;
    banner = document.createElement('aside');
    banner.className = 'mira-analytics-choice';
    banner.setAttribute('aria-label', 'Preferência de métricas');
    const message = document.createElement('p');
    message.textContent = 'Podemos usar o Google Analytics para entender visitas e cliques nas ofertas? O site funciona normalmente sem isso.';
    const actions = document.createElement('div');
    const accept = document.createElement('button');
    accept.type = 'button'; accept.textContent = 'Aceitar métricas';
    accept.addEventListener('click', () => save('granted'));
    const decline = document.createElement('button');
    decline.type = 'button'; decline.textContent = 'Agora não';
    decline.addEventListener('click', () => save('denied'));
    const details = document.createElement('a');
    details.href = new URL('privacidade.html', scriptUrl).href;
    details.textContent = 'Privacidade';
    actions.append(accept,decline,details);
    banner.append(message,actions);
    document.body.append(banner);
  }

  document.addEventListener('click', track, {capture:true});
  document.addEventListener('auxclick', track, {capture:true});
  document.addEventListener('click', event => {
    if (event.target?.closest?.('[data-analytics-preferences]')) showBanner();
  });
  window.MiraAnalytics = {
    openPreferences:showBanner,
    snapshot:() => Array.from(counts, ([params,count]) => ({...JSON.parse(params),count})),
    reset:() => counts.clear(),
  };
  if (!configured) {
    document.querySelectorAll('[data-analytics-preferences]').forEach(button => { button.hidden = true; });
    return;
  }
  if (choice === 'granted') start();
  else if (choice !== 'denied') {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded',showBanner,{once:true});
    else showBanner();
  }
})();
