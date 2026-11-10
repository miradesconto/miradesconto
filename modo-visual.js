/* Preserva a escolha do visitante sem alterar os dados de ofertas. */
(() => {
  'use strict';
  const KEY = 'miradesconto-modo-visual';
  const isGamer = document.documentElement.getAttribute('data-mira-layout') === 'gamer';
  const read = () => {
    try { return window.localStorage.getItem(KEY); } catch (_) { return null; }
  };
  const write = value => {
    try { window.localStorage.setItem(KEY, value); } catch (_) {}
  };

  // O Clássico é padrão para visitantes novos. Só redireciona quem
  // escolheu o modo Gamer explicitamente em outra visita.
  const pathname = window.location.pathname;
  const isHome = pathname === '/' || pathname.endsWith('/index.html');
  if (!isGamer && isHome && read() === 'gamer') {
    const target = new URL('gamer.html', window.location.href);
    window.location.replace(target.href);
    return;
  }

  document.querySelectorAll('[data-layout-option]').forEach(link => {
    link.addEventListener('click', () => {
      const choice = link.getAttribute('data-layout-option');
      if (choice === 'classic' || choice === 'gamer') write(choice);
    });
  });
})();