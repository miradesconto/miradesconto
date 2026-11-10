/* Shopee premium: protege as imagens sem interferir no clique de afiliado. */
(() => {
  'use strict';
  document.querySelectorAll('.shopee-feature-photo, .shopee-find-photo').forEach(frame => {
    const img = frame.querySelector('img');
    const fallback = frame.querySelector('.shopee-photo-fallback');
    if (!img || !fallback) return;
    const original = img.getAttribute('src') || '';
    let attempts = [];
    if (original.startsWith('https://cf.shopee.com.br/file/')) {
      const path = original.substring('https://cf.shopee.com.br'.length);
      attempts = ['https://down-br.img.susercontent.com' + path,
                  'https://down-bs-br.img.susercontent.com' + path];
    }
    img.addEventListener('error', () => {
      if (attempts.length) {
        img.src = attempts.shift();
      } else {
        img.hidden = true;
        fallback.hidden = false;
      }
    });
  });
})();
