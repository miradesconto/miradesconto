'use strict';
(() => {
  const id = String(window.MIRA_GA4_ID || '').trim().toUpperCase();
  if (!/^G-[A-Z0-9]{5,20}$/.test(id)) return;
  const scriptUrl = document.currentScript?.src || new URL('analytics.js', window.location.href).href;
  const key = 'mira_analytics_consent_v1';
  let choice;
  try { choice = localStorage.getItem(key); } catch { choice = null; }
  let started = false;

  function start() {
    if (started) return;
    started = true;
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag('js', new Date());
    window.gtag('config', id, {send_page_view: true});
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
    if (choice !== 'granted' || !started) return;
    const link = event.target?.closest?.('a[href]');
    if (!link || !isAffiliate(link.href)) return;
    const catalog = window.MIRA_DATA?.products || [];
    const product = catalog.find(p => p.affiliateUrl === link.href);
    const location = link.closest('.hero') ? 'hero' :
      link.closest('#productList') ? 'catalog' : link.closest('article') ? 'article' : 'other';
    const params = {
      link_location: location,
      affiliate_host: new URL(link.href).hostname,
      item_name: String(product?.name || link.textContent || '').trim().slice(0,100),
    };
    if (product?.id) params.item_id = product.id;
    if (product?.category) params.item_category = product.category;
    if (typeof product?.price === 'number' && Number.isFinite(product.price)) {
      params.item_price = product.price;
      params.currency = 'BRL';
    }
    window.gtag('event', 'affiliate_click', params);
  }

  let banner;
  function hideBanner() { banner?.remove(); banner = null; }
  function save(value) {
    choice = value;
    try { localStorage.setItem(key, value); } catch { /* Navegação continua sem armazenamento. */ }
    hideBanner();
    if (value === 'granted') start();
  }
  function showBanner() {
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
  document.addEventListener('click', event => {
    if (event.target?.closest?.('[data-analytics-preferences]')) showBanner();
  });
  window.MiraAnalytics = {openPreferences:showBanner};
  if (choice === 'granted') start();
  else if (choice !== 'denied') {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded',showBanner,{once:true});
    else showBanner();
  }
})();
