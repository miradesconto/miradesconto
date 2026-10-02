'use strict';
const form = document.getElementById('form');
const status = document.getElementById('status');
const input = document.getElementById('links');
const incoming = new URL(location.href).searchParams.get('link');
if (incoming) input.value = incoming;
history.replaceState(null, '', location.pathname);
const panel = new URL('./', location.href).href;
document.getElementById('bookmark').href = 'javascript:' + encodeURIComponent(`(()=>{const link=prompt('Cole o link oficial de afiliado gerado no Mercado Livre:');if(link)window.open(${JSON.stringify(panel)}+'?link='+encodeURIComponent(link),'_blank','noopener,noreferrer');})()`);
form.addEventListener('submit', async event => {
  event.preventDefault();
  const links = input.value.trim().split(/\s+/);
  if (!links.length || links.length > 20 || links.some(link => !/^https:\/\/(?:meli\.la\/[A-Za-z0-9]+|(?:www\.)?mercadolivre\.com(?:\.br)?\/sec\/[A-Za-z0-9]+)$/.test(link))) {
    status.textContent = 'Use até 20 links oficiais meli.la ou Mercado Livre /sec/.'; return;
  }
  const tokenInput = document.getElementById('token');
  const token = tokenInput.value.trim();
  const button = document.getElementById('submit');
  button.disabled = true;
  status.textContent = 'Enviando solicitação…';
  try {
    const response = await fetch('https://api.github.com/repos/miradesconto/miradesconto/actions/workflows/import-affiliate-links.yml/dispatches', {
      method: 'POST', headers: {'Accept':'application/vnd.github+json','Authorization':'Bearer '+token,'Content-Type':'application/json'},
      body: JSON.stringify({ref:'main',inputs:{links:links.join('\n')}})
    });
    if (!response.ok) throw new Error(response.status === 401 || response.status === 403 ? 'Autorização inválida ou sem permissão Actions: escrita.' : 'GitHub recusou a solicitação (HTTP '+response.status+').');
    status.textContent = 'Solicitação recebida. Acompanhe o resultado no GitHub pelo link abaixo. A publicação só ocorre após a confirmação do produto e do preço.';
  } catch (error) { status.textContent = error.message; }
  finally { tokenInput.value = ''; button.disabled = false; }
});
