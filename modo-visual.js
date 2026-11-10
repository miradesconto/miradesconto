/* O MiraDesconto tem UMA página e dois temas. Nunca navega ou recria o catálogo. */
(() => {
  'use strict';

  const KEY = 'miradesconto-modo-visual';
  const html = document.documentElement;
  const allowed = value => value === 'classic' || value === 'gamer';
  const safeRead = () => {
    try { return window.localStorage.getItem(KEY); } catch (_) { return null; }
  };
  const safeWrite = value => {
    try { window.localStorage.setItem(KEY, value); } catch (_) {}
  };
  const requested = new URLSearchParams(window.location.search).get('modo');
  const mode = allowed(requested) ? requested : (allowed(safeRead()) ? safeRead() : 'classic');

  function apply(next, persist) {
    if (!allowed(next)) return;

    html.setAttribute('data-mira-layout', next);
    document.body.classList.toggle('mira-mode-dark', next === 'gamer');

    document.querySelectorAll('[data-layout-option]').forEach(link => {
      const selected = link.getAttribute('data-layout-option') === next;
      if (selected) {
        link.setAttribute('aria-current', 'true');
      } else {
        link.removeAttribute('aria-current');
      }
    });

    const themeColor = document.querySelector('meta[name="theme-color"]');
    if (themeColor) themeColor.setAttribute('content', next === 'gamer' ? '#080f1d' : '#0f172a');
    if (persist) safeWrite(next);
  }

  // Um link para ?modo=gamer também funciona quando o usuário não tem JS.
  apply(mode, allowed(requested));
  if (allowed(requested)) {
    // Remove somente o parâmetro de apresentação; preserve busca/hash/outros parâmetros.
    try {
      const url = new URL(window.location.href);
      url.searchParams.delete('modo');
      window.history.replaceState(window.history.state, '', url.pathname + url.search + url.hash);
    } catch (_) {}
  }

  document.querySelectorAll('[data-layout-option]').forEach(link => {
    link.addEventListener('click', event => {
      if (event.defaultPrevented || event.button !== 0 || event.metaKey ||
          event.ctrlKey || event.shiftKey || event.altKey) return;
      const next = link.getAttribute('data-layout-option');
      if (!allowed(next)) return;
      event.preventDefault();

      // Alterna as cores/cards existentes in-place: sem reload, sem perder
      // texto digitado, filtros, scroll, estado do carrinho ou histórico de produtos.
      apply(next, true);
    });
  });
})();
