'use strict';
(() => {
  const form = document.getElementById('associar-form');
  const selectedId = document.getElementById('associar-id');
  const link = document.getElementById('associar-url');
  const token = document.getElementById('associar-token');
  const send = document.getElementById('associar-enviar');
  const status = document.getElementById('associar-status');
  const validAffiliate = url => /^https:\/\/(?:meli\.la\/[A-Za-z0-9]+|(?:www\.)?mercadolivre\.com(?:\.br)?\/sec\/[A-Za-z0-9]+)$/.test(url);

  form.addEventListener('submit', async event => {
    event.preventDefault();
    const productId = selectedId.value.trim();
    const affiliateUrl = link.value.trim();
    const authorization = token.value.trim();
    if (!/^MLB\d{7,}$/.test(productId)) {
      status.textContent = 'Selecione um produto válido antes de cadastrar o link.';
      return;
    }
    if (!validAffiliate(affiliateUrl)) {
      status.textContent = 'Use o link oficial meli.la ou Mercado Livre /sec/.';
      return;
    }
    if (!authorization) {
      status.textContent = 'É necessário um token com permissão Actions: escrita.';
      return;
    }
    send.disabled = true;
    status.textContent = 'Enviando solicitação de revisão…';
    try {
      const response = await fetch(
        'https://api.github.com/repos/miradesconto/miradesconto/actions/workflows/associate-affiliate-link.yml/dispatches', {
          method: 'POST',
          headers: {
            'Accept': 'application/vnd.github+json',
            'Authorization': 'Bearer ' + authorization,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            ref: 'main',
            inputs: { product_id: productId, affiliate_url: affiliateUrl }
          })
        }
      );
      if (!response.ok) {
        const message = response.status === 401 || response.status === 403 ?
          'GitHub recusou a autorização. Verifique o token e suas permissões.' :
          'GitHub recusou a solicitação (HTTP ' + response.status + ').';
        throw new Error(message);
      }
      status.textContent = 'Solicitação recebida pelo GitHub. Consulte a execução: ela poderá recusar links de listas, perfis, outras variantes ou páginas bloqueadas. Se passar, será aberto um PR em rascunho para aprovação. O site ainda não foi alterado.';
      link.value = '';
    } catch (error) {
      status.textContent = error.message;
    } finally {
      token.value = '';
      send.disabled = false;
    }
  });
})();
