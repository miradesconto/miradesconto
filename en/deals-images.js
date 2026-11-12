'use strict';
// Leave product imagery truthful: show a text fallback, never a different product.
document.querySelectorAll('.en-deal-card-media img').forEach(image => {
  const fallback = image.nextElementSibling;
  const fail = () => { image.hidden = true; if (fallback) fallback.hidden = false; };
  const success = () => { image.hidden = false; if (fallback) fallback.hidden = true; };
  image.addEventListener('error', fail);
  image.addEventListener('load', success);
  if (image.complete) (image.naturalWidth > 0 ? success : fail)();
});
