#!/usr/bin/env python3
"""Gera destinos permanentes para Pins e valida o cadastro adicional de afiliados."""
import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlsplit, parse_qs, urlencode
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'integracoes'))
import catalogo

def platform(value):
    if not isinstance(value,str): return None
    u=urlsplit(value)
    if u.scheme!='https' or u.username or u.password or u.port: return None
    if u.hostname=='meli.la' and re.fullmatch(r'/[A-Za-z0-9]+/?',u.path) and value not in ('https://meli.la/1NguveN','https://meli.la/1pyBZm8'): return 'mercadolivre'
    if u.hostname in ('amzn.to','a.co') and re.fullmatch(r'/[A-Za-z0-9]+/?',u.path): return 'amazon'
    if u.hostname in ('amazon.com.br','www.amazon.com.br') and parse_qs(u.query).get('tag') and re.search(r'/(?:dp|gp/product)/[A-Z0-9]{10}(?:/|$)',u.path,re.I): return 'amazon'
    if u.hostname in ('s.shopee.com.br','shope.ee') and re.fullmatch(r'/[A-Za-z0-9]+/?',u.path): return 'shopee'
    return None

def validate_extras(entries, existing):
    if not isinstance(entries,list): raise ValueError('Cadastro adicional deve ser uma lista')
    ids={p['id'] for p in existing};links={p.get('affiliateUrl') for p in existing}
    for p in entries:
        for key in ('id','name','category','store','affiliateUrl','imageUrl','productUrl'):
            if not isinstance(p.get(key),str) or not p[key].strip(): raise ValueError('Campo obrigatório: '+key)
        if not re.fullmatch(r'(?:AMZ|SHP|EXT)-[a-z0-9][a-z0-9-]{2,79}',p['id']): raise ValueError('Use ID AMZ-, SHP- ou EXT- seguido de slug minúsculo')
        if p['id'] in ids or p['affiliateUrl'] in links: raise ValueError('ID ou link repetido: '+p['id'])
        store=platform(p['affiliateUrl'])
        if not store or p.get('affiliateVerified') is not True or p.get('affiliateLinkType')!='product': raise ValueError('É necessário confirmar o link individual gerado na própria conta')
        if p['store']!={'amazon':'Amazon','shopee':'Shopee','mercadolivre':'Mercado Livre'}[store]: raise ValueError('Loja diverge do domínio')
        for key in ('imageUrl','productUrl'):
            u=urlsplit(p[key])
            if u.scheme!='https' or not u.hostname or u.username or u.password: raise ValueError('URL HTTPS inválida: '+key)
        if any(k in p for k in ('price','oldPrice','discount','priceCheck')): raise ValueError('Não inserir preços sem integração de verificação; estes anúncios usam consulta na loja')
        ids.add(p['id']);links.add(p['affiliateUrl'])
    return entries

def render(root=ROOT):
    source=catalogo.read_json(root/'dados/catalogo.json')
    current=catalogo.public_data(source)['products']
    extras=validate_extras(catalogo.read_json(root/'_data/afiliados_extras.json'),current)
    guides={}
    for article in sorted((root/'_artigos').glob('*.md')):
        text=article.read_text();front=text.split('---',2)[1]
        if not re.search(r'^status:\s*[\"\']?publicado',front,re.M): continue
        match=re.search(r'^produtos:\s*(\[[^\n]*\])',front,re.M)
        if match:
            for id in re.findall(r'MLB\d{7,}',match[1]): guides.setdefault(id,'/blog/'+article.stem+'/')
    # Keep existing destinations even when a product rotates out of the homepage.
    prior_file=root/'_data/ofertas_site.json'
    prior=catalogo.read_json(prior_file) if prior_file.exists() else {}
    source_by_id={p['id']:p for p in source['products']}
    active={p['id']:p for p in current+extras}
    for id,old in prior.items():
        if id not in active:
            active[id]=source_by_id.get(id,dict(old,available=False))
    mapping={};files={};pin_rows=[]
    for p in active.values():
        if not platform(p.get('affiliateUrl')) or p.get('affiliateLinkType')=='list': continue
        # Quarantine implausible offers; never build a campaign around them.
        from qualidade import price_review_reason
        if price_review_reason(p): continue
        item=dict(p);item['landingUrl']='/oferta/'+p['id'].lower()+'/'
        if p['id'] in guides:item['guideUrl']=guides[p['id']]
        mapping[p['id']]=item
        front={'layout':'oferta','permalink':item['landingUrl'],'product_id':p['id'],'title':p['name'],'description':'Confira '+p['name'][:130]+': detalhes do anúncio, loja e condições de compra no MiraDesconto.'}
        files['_ofertas/'+p['id'].lower()+'.md']='---\n'+'\n'.join(k+': '+json.dumps(v,ensure_ascii=False) for k,v in front.items())+'\n---\n'
        pin_rows.append({'id':p['id'],'title':p['name'][:100],'destination':'https://miradesconto.com.br'+item['landingUrl']+'?'+urlencode({'utm_source':'pinterest','utm_medium':'organic_social','utm_campaign':'black_friday_2026','utm_content':p['id'].lower()}),'image':p['imageUrl'],'affiliateDisclosure':'Publicidade · Link de afiliado','status':'rascunho — imagem e oferta devem ser conferidas antes de publicar'})
    cfg=catalogo.read_json(root/'_data/black_friday.json')
    if len(cfg['selectedIds'])!=len(set(cfg['selectedIds'])):raise ValueError('Seleção da campanha repetida')
    missing=set(cfg['selectedIds'])-mapping.keys()
    if missing:raise ValueError('Produto da campanha sem destino válido: '+', '.join(sorted(missing)))
    files['_data/ofertas_site.json']=catalogo.dumps(mapping,pretty=True)+'\n'
    files['produtos-extras.js']='// Gerado por integracoes/campanha.py; links confirmados pelo proprietário.\nwindow.MIRA_EXTRA_PRODUCTS = '+catalogo.dumps(extras)+';\nif (window.MIRA_DATA && window.MiraAffiliate) window.MIRA_DATA.products = window.MiraAffiliate.merge(window.MIRA_DATA.products);\n'
    files['docs/pinterest-destinos.json']=catalogo.dumps(pin_rows,pretty=True)+'\n'
    return files

def generate(check=False,root=ROOT):
    files=render(root)
    stale=[p for p in (root/'_ofertas').glob('*.md') if p.relative_to(root).as_posix() not in files]
    if check:
        errors=[n for n,t in files.items() if not (root/n).exists() or (root/n).read_text()!=t]
        if errors or stale: raise ValueError('Campanha desatualizada: '+', '.join(errors+[p.name for p in stale]))
    else:
        for p in stale:p.unlink()
        for name,text in files.items():
            target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(text)
    return files

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');parser.add_argument('--select-pending',action='store_true');args=parser.parse_args()
    if args.select_pending:
        pending=catalogo.read_json(ROOT/'integracoes/mercadolivre/cadastro-pendente.json')
        source=catalogo.public_data(catalogo.read_json(ROOT/'dados/catalogo.json'))['products']
        valid=render(ROOT)
        offers=json.loads(valid['_data/ofertas_site.json'])
        selected=[p['id'] for link in pending['links'] for p in source if p.get('affiliateUrl')==link and p['id'] in offers]
        cfg=catalogo.read_json(ROOT/'_data/black_friday.json')
        cfg['selectedIds']=list(dict.fromkeys(selected+cfg['selectedIds']))[:10]
        (ROOT/'_data/black_friday.json').write_text(catalogo.dumps(cfg,pretty=True)+'\n')
        print(str(len(selected))+' produtos confirmados deste lote na seleção da campanha')
    generate(args.check);print('Campanha, destinos dos Pins e cadastro adicional consistentes')
