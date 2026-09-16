'use strict';
(() => {
    const hero = document.querySelector('.hero');
    const groups = [
        {category:'Informática',label:'Tecnologia',title:'Ofertas que valem a pena.',text:'Encontre acessórios e novidades para o seu dia a dia conectado.'},
        {category:'Casa',label:'Sua casa',title:'Mais conforto. Boas escolhas.',text:'Descubra produtos para cuidar da casa e facilitar sua rotina.'},
        {category:'Moda',label:'Seu estilo',title:'Seu próximo achado está aqui.',text:'Explore roupas, calçados e acessórios em um só lugar.'}
    ];
    const slides = groups.map(g=>({...g,items:products.filter(p=>p.category===g.category && safeUrl(p.imageUrl) && (g.category!=='Informática' || /teclado|impressora|mouse/i.test(p.name))).slice(0,3)})).filter(g=>g.items.length);
    if (!hero || !slides.length) return;
    hero.setAttribute('aria-label','Destaques por categoria');
    hero.setAttribute('aria-roledescription','carrossel');
    const shell=element('div','hero-shell');
    const panels=slides.map((g,i)=>{
        const panel=element('div','hero-slide');
        panel.setAttribute('role','group');panel.setAttribute('aria-roledescription','slide');
        panel.setAttribute('aria-label',`${i+1} de ${slides.length}: ${g.label}`);
        const copy=element('div','hero-copy');
        copy.append(element('div','hero-eyebrow',`MiraDesconto / ${g.label}`),element(i===0?'h1':'h2','',g.title),element('p','',g.text));
        const cta=element('button','hero-cta',`Explorar ${g.label.toLowerCase()} →`);cta.type='button';
        cta.addEventListener('click',()=>{
            $('searchInput').value='';$('sortSelect').value='default';
            const category=[...categoryContainer.children].find(b=>b.dataset.category===g.category);
            if(category)selectCategory(category);
            $('sectionTitle').setAttribute('tabindex','-1');$('sectionTitle').focus({preventScroll:true});
            $('sectionTitle').scrollIntoView({behavior:'auto',block:'start'});
        });copy.append(cta);
        const art=element('div','hero-art');
        g.items.forEach(p=>{const tile=element('div','hero-product');const img=element('img');img.src=p.imageUrl;img.alt=p.name;img.width=240;img.height=240;img.decoding='async';img.addEventListener('error',()=>{tile.replaceChildren(element('span','','Imagem indisponível'));},{once:true});tile.append(img);art.append(tile);});
        panel.append(copy,art);shell.append(panel);return panel;
    });
    const controls=element('div','hero-controls');
    function button(label,text,cls='hero-control'){const b=element('button',cls,text);b.type='button';b.setAttribute('aria-label',label);return b;}
    const prev=button('Banner anterior','‹'), next=button('Próximo banner','›');
    const dots=element('div','hero-dots');
    const dotButtons=slides.map((g,i)=>{const b=button(`Mostrar banner ${g.label}`,'','hero-dot');b.addEventListener('click',()=>show(i));dots.append(b);return b;});
    const pause=button('Pausar troca automática','Pausar','hero-control hero-pause');
    controls.append(prev,dots,next,pause);shell.append(controls,element('p','hero-caption','Imagens de produtos do catálogo. Confira preços e disponibilidade nas ofertas.'));
    hero.replaceChildren(shell);
    let current=0,timer=null,hover=false,focused=false;
    const motion=matchMedia('(prefers-reduced-motion: reduce)');let paused=motion.matches;
    function schedule(){clearTimeout(timer);if(!paused&&!hover&&!focused&&!document.hidden)timer=setTimeout(()=>show((current+1)%slides.length),5000);}
    function show(i){current=(i+slides.length)%slides.length;panels.forEach((p,j)=>p.hidden=j!==current);dotButtons.forEach((b,j)=>b.setAttribute('aria-pressed',String(j===current)));schedule();}
    function pauseLabel(){pause.textContent=paused?'Reproduzir':'Pausar';pause.setAttribute('aria-label',paused?'Iniciar troca automática':'Pausar troca automática');}
    prev.addEventListener('click',()=>show(current-1));next.addEventListener('click',()=>show(current+1));
    pause.addEventListener('click',()=>{paused=!paused;pauseLabel();schedule();});
    hero.addEventListener('mouseenter',()=>{hover=true;schedule();});hero.addEventListener('mouseleave',()=>{hover=false;schedule();});
    hero.addEventListener('focusin',()=>{focused=true;schedule();});hero.addEventListener('focusout',e=>{if(!hero.contains(e.relatedTarget)){focused=false;schedule();}});
    document.addEventListener('visibilitychange',schedule);
    motion.addEventListener('change',e=>{paused=e.matches;pauseLabel();schedule();});
    pauseLabel();show(0);
})();
