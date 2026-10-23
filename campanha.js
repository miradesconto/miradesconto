/* Atualiza apenas preços com evidência; HTML e compra funcionam sem JavaScript. */
'use strict';
(() => {
  const cards=[...document.querySelectorAll('[data-offer-id]')];
  const money=n=>n.toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
  function render() {
    const products=new Map((window.MIRA_DATA?.products || []).map(p=>[p.id,p]));
    let fresh=0;
    for (const card of cards) {
      const p=products.get(card.dataset.offerId);
      const valid=p && window.MiraQuality?.usablePrice(p)===true;
      card.querySelector('[data-offer-price]').textContent=valid?money(p.price):'Consultar preço na loja';
      card.querySelector('[data-offer-checked]').textContent=valid?'Conferido em '+new Date(p.priceCheck.checkedAt).toLocaleString('pt-BR',{timeZone:'America/Sao_Paulo'})+' (Brasília). Confirme Pix, cupom e frete.':'Preço atual não confirmado. Consulte as condições na loja.';
      if (valid) fresh++;
    }
    const status=document.getElementById('campaignStatus');
    if(status) status.textContent=fresh?fresh+' produtos com preço conferido nas últimas 2 horas. Demais valores: consulte na loja.':'Confira os valores atuais nos anúncios. A seleção não garante desconto de Black Friday.';
  }
  const category=document.getElementById('campaignCategory');
  category?.addEventListener('change',()=>{
    for(const card of cards) card.hidden=!!category.value && card.dataset.category!==category.value;
  });
  for(const image of document.querySelectorAll('.campaign-photo img,.offer-photo img')) image.addEventListener('error',()=>{image.hidden=true;const text=document.createElement('p');text.textContent='Imagem indisponível. Veja o produto no anúncio.';image.parentElement.append(text);});
  async function refresh() {
    if(document.hidden)return;
    try {
      const r=await fetch('/produtos.js',{cache:'no-store'});if(!r.ok)return;
      const text=await r.text();const match=text.match(/(?:^|\n)window\.MIRA_DATA\s*=\s*(\{[\s\S]*\})\s*;?\s*$/);if(!match)return;
      const data=JSON.parse(match[1]);
      if(!Array.isArray(data.products)||!data.products.length||data.products.some(p=>!p?.id||!p.name)||new Set(data.products.map(p=>p.id)).size!==data.products.length)return;
      window.MIRA_DATA.products=window.MiraAffiliate.merge(data.products);render();
    }catch{/* Preserva o catálogo anterior; preços vencidos continuam ocultos. */}
  }
  render();refresh();setInterval(render,60000);setInterval(refresh,300000);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden){render();refresh();}});
})();
