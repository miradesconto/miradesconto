'use strict';
window.MiraHistory = (() => {
  let historyBase = null;
  try {
    const raw = window.MIRA_HISTORY_CONFIG?.apiBaseUrl;
    if (raw) {
      const url = new URL(raw);
      const local = ['localhost','127.0.0.1'].includes(url.hostname);
      if ((url.protocol === 'https:' || (local && url.protocol === 'http:'))
          && !url.username && !url.password && !url.search && !url.hash && url.pathname === '/') historyBase = url;
    }
  } catch { /* Configuração pendente: o modal informa indisponibilidade. */ }
  const fmt = n => n.toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
  const date = at => new Date(at).toLocaleString('pt-BR',{timeZone:'America/Sao_Paulo'});
  function node(tag, text) { const e=document.createElement(tag); if(text!==undefined)e.textContent=text; return e; }
  async function open(product, trigger) {
    const dialog=node('dialog'); dialog.className='history-dialog';
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);
    const close=node('button','Fechar ×'); close.type='button';
    close.addEventListener('click',()=>dialog.close());
    dialog.addEventListener('close',()=>{controller.abort();clearTimeout(timeout);dialog.remove();trigger?.focus();});
    const title=node('h2','Histórico de preço'); title.id='history-title';dialog.setAttribute('aria-labelledby',title.id);
    const body=node('div','Carregando registros…'); body.setAttribute('aria-live','polite');
    dialog.append(close,title,node('p',product.name),body);document.body.append(dialog);dialog.showModal();
    try {
      if (!historyBase) throw Error('disabled');
      if (!/^MLB\d{7,14}$/.test(product.id)) throw Error('invalid');
      const response=await fetch(new URL('/api/history/'+product.id,historyBase),
        {signal:controller.signal,cache:'no-store',credentials:'omit'});
      if(response.status===404)throw Error('missing');
      if(!response.ok)throw Error('unavailable');
      const data=await response.json();
      if(data.schemaVersion!==1 || data.productId!==product.id || data.currency!=='BRL' || !Array.isArray(data.observations))throw Error('invalid');
      const evidence=product.priceCheck || {};
      const expected=evidence.method==='ml-sale-price-v1'?product.itemId:product.id;
      const rows=data.observations.filter(r=>r && r.itemId===expected && String(r.variationId ?? '')===String(evidence.variationId ?? '')
        && ['poly-card-v1','ml-sale-price-v1','ml-edge-item-v1'].includes(r.method)
        && Number.isFinite(r.price) && r.price>0 && Number.isFinite(Date.parse(r.at))
        && Date.parse(r.at)<=Date.now() && Date.parse(r.at)>=Date.now()-180*86400000).sort((a,b)=>Date.parse(a.at)-Date.parse(b.at));
      if(!rows.length)throw Error('missing');
      body.replaceChildren();
      body.append(node('p','Primeiro registro disponível: '+date(rows[0].at)+'. Coletas podem ter lacunas; o gráfico não representa todos os preços praticados pela loja.'));
      const controls=node('div'); const chart=node('div');
      for(const days of [30,90,180]) {
        const b=node('button',days+' dias');b.type='button';b.addEventListener('click',()=>render(days));b.dataset.days=days;controls.append(b);
      }
      body.append(controls,chart,node('p','Preço do anúncio observado, sem frete e sem aplicar cupons pessoais. “Referência da loja” é o valor informado por ela, não um preço histórico comprovado. Comparação restrita ao mesmo anúncio e à identificação de variação disponível.'));
      function render(days) {
        controls.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(Number(b.dataset.days)===days)));
        const selected=rows.filter(r=>Date.parse(r.at)>=Date.now()-days*86400000);
        chart.replaceChildren();
        if(!selected.length){chart.append(node('p','Sem observações verificadas neste período.'));return;}
        const values=selected.map(r=>r.price), min=Math.min(...values),max=Math.max(...values);
        chart.append(node('p',`${selected.length} observações · Menor: ${fmt(min)} · Maior: ${fmt(max)}`));
        const recent=typeof MiraQuality!=='undefined' && MiraQuality.usablePrice(product);
        if(recent) {
          const same=product.price<=min;
          chart.append(node('p',same?'Preço atual igual ou inferior ao menor registrado no período disponível.':'Preço atual '+fmt(product.price)+' · '+((product.price/min-1)*100).toFixed(1).replace('.',',')+'% acima do menor observado.'));
          if(product.oldPrice>product.price)chart.append(node('p',Math.round((1-product.price/product.oldPrice)*100)+'% abaixo da referência exibida pela loja ('+fmt(product.oldPrice)+').'));
        } else chart.append(node('p','Preço atual sem verificação recente. Consulte a loja.'));
        const ns='http://www.w3.org/2000/svg';const svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 640 220');svg.setAttribute('role','img');svg.setAttribute('aria-label','Preços observados entre '+date(selected[0].at)+' e '+date(selected.at(-1).at));
        const start=Date.parse(selected[0].at),span=Math.max(1,Date.parse(selected.at(-1).at)-start), range=Math.max(1,max-min);
        const coords=selected.map(r=>[20+600*(Date.parse(r.at)-start)/span,190-160*(r.price-min)/range]);
        const line=document.createElementNS(ns,'polyline');line.setAttribute('points',coords.map(p=>p.join(',')).join(' '));line.setAttribute('fill','none');line.setAttribute('stroke','#15803d');line.setAttribute('stroke-width','3');svg.append(line);
        for(const [x,y] of coords){const c=document.createElementNS(ns,'circle');c.setAttribute('cx',x);c.setAttribute('cy',y);c.setAttribute('r','3');c.setAttribute('fill','#15803d');svg.append(c);}
        for(const [label,y] of [[fmt(max),18],[fmt(min),214]]){const t=document.createElementNS(ns,'text');t.setAttribute('x','20');t.setAttribute('y',y);t.setAttribute('font-size','12');t.setAttribute('fill','#475569');t.textContent=label;svg.append(t);}
        chart.append(svg,node('p',date(selected[0].at)+' → '+date(selected.at(-1).at)));
        const details=node('details');details.append(node('summary','Consultar registros e valores'));
        const table=node('table'),head=node('tr');for(const t of ['Data da coleta','Preço observado','Referência da loja'])head.append(node('th',t));table.append(head);
        for(const r of [...selected].reverse()){const tr=node('tr');tr.append(node('td',date(r.at)),node('td',fmt(r.price)),node('td',typeof r.reference==='number'&&r.reference>0?fmt(r.reference):'Não informada'));table.append(tr);}
        details.append(table);chart.append(details);
      }
      render(180);
    } catch (error) {
      body.textContent=error.message==='missing'
        ? 'Ainda não há histórico disponível para este anúncio e variação. Os registros serão acumulados nas próximas coletas verificadas.'
        : error.message==='disabled' ? 'A consulta de histórico está em implantação.'
        : 'Não foi possível consultar o histórico agora. Tente novamente mais tarde.';
    } finally {clearTimeout(timeout);}
  }
  return {open};
})();
