"""Publicação Telegram: seleção verificável, reserva durável e POST sem replay."""
from __future__ import annotations
import argparse, hashlib, html, io, json, math, os, re, sys, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
import requests
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'integracoes'))
from qualidade import usable_price
from tech_policy import eligible as tech_eligible

class PublishError(RuntimeError): pass

def origin(value):
    p=urlsplit(value)
    if p.scheme!='https' or not p.hostname or p.username or p.password or p.path not in ('','/') or p.query or p.fragment:
        raise PublishError('Configure uma origem HTTPS, sem caminho ou credenciais')
    return value.rstrip('/')

def stamp(value):
    try:
        dt=datetime.fromisoformat(value.replace('Z','+00:00'))
        return dt if dt.tzinfo else None
    except (ValueError,AttributeError,TypeError): return None

def positive(value):
    return not isinstance(value,bool) and isinstance(value,(int,float)) and math.isfinite(value) and value>0

def select_offer(products,radar,registry,now):
    generated=stamp(radar.get('generatedAt'))
    if not generated or not 0 <= (now-generated).total_seconds() <= 6*3600: return None
    candidates=[]
    for p in products:
        i=p.get('id');r=(radar.get('byId') or {}).get(i);ev=p.get('priceCheck') or {};checked=stamp(ev.get('checkedAt'))
        if not isinstance(r,dict) or i not in registry or not re.fullmatch(r'MLB\d{7,14}',str(i)): continue
        if not usable_price(p,now) or not checked or not 0 <= (now-checked).total_seconds() <= 2*3600: continue
        if p.get('available') is False or p.get('availabilityStatus') in ('unavailable','out_of_stock'): continue
        if not tech_eligible(p) or not isinstance(p.get('name'),str) or not p['name'].strip(): continue
        if r.get('actionable') is not True or r.get('currentPrice')!=p.get('price') or r.get('checkedAt')!=ev.get('checkedAt'): continue
        if not positive(r.get('averagePrice')) or not positive(r.get('minimumPrice')): continue
        if not positive(r.get('spanDays')) or r['spanDays']<7 or not positive(r.get('observations')) or r['observations']<6: continue
        if r['minimumPrice']>p['price']: continue
        # Registry/price evidence must describe the same variation.
        if ev.get('itemId') != i or registry[i].get('variationId') != ev.get('variationId'): continue
        delta=(p['price']/r['averagePrice']-1)*100
        if p['price']>r['averagePrice'] or (p['price']>r['minimumPrice'] and delta>-2): continue
        candidates.append((delta,-r['spanDays'],str(i),p,r))
    if not candidates: return None
    *_,p,r=min(candidates,key=lambda row:row[:3]);return p,r

def money(value):
    return 'R$ '+f'{value:,.2f}'.replace(',','X').replace('.',',').replace('X','.')

def build_post(product,radar,base,text_only=False):
    link=origin(base)+'/go/'+product['id']
    name=re.sub(r'\s+',' ',product['name']).strip()[:180]
    delta=(product['price']/radar['averagePrice']-1)*100
    angle='No menor valor observado neste anúncio.' if product['price']<=radar['minimumPrice'] else f'{abs(delta):.1f}% abaixo da média observada.'
    checked=stamp(product['priceCheck']['checkedAt']).astimezone(__import__('zoneinfo').ZoneInfo('America/Sao_Paulo'))
    text=(f'🎯 <b>OFERTA NA MIRA</b>\n\n<b>{html.escape(name)}</b>\n'
          f'💰 <b>{money(product["price"])}</b>\n{angle}\n'
          f'Média observada: {money(radar["averagePrice"])} · {int(radar["spanDays"])} dias acompanhados.\n'
          f'Conferido em {checked:%d/%m às %H:%M} (Brasília).\n\n'
          f'👉 <a href="{html.escape(link,quote=True)}">Conferir oferta</a>\n\n'
          'Preço e estoque podem mudar. Confira frete e condições na loja.\n'
          'Link de afiliado: pode gerar comissão sem custo adicional.')
    image=product.get('imageUrl') or '';u=urlsplit(image)
    use_photo=not text_only and u.scheme=='https' and u.hostname=='http2.mlstatic.com' and not u.username and not u.password
    # Telegram retrieves the official URL. No automatic text fallback after an uncertain POST.
    method='sendPhoto' if use_photo else 'sendMessage'
    field='caption' if use_photo else 'text'
    if len(text.encode('utf-16-le'))//2 > (1024 if use_photo else 4096): raise PublishError('Texto excede o limite Telegram')
    body={field:text,'parse_mode':'HTML','reply_markup':{'inline_keyboard':[[{'text':'Conferir oferta','url':link}]]}}
    if use_photo: body['photo']=image
    else: body['link_preview_options']={'is_disabled':True}
    key=json.dumps([product['id'],product['priceCheck'].get('variationId'),f"{product['price']:.2f}"],separators=(',',':'))
    return {'method':method,'body':body,'fingerprint':hashlib.sha256(key.encode()).hexdigest(),'link':link,'productId':product['id']}

def prepare_photo(post,session):
    if post['method']!='sendPhoto': return post,None
    response=None
    try:
        started=time.monotonic()
        response=session.get(post['body']['photo'],stream=True,allow_redirects=False,timeout=(5,10))
        if response.status_code!=200: raise ValueError()
        chunks=[];size=0
        for chunk in response.iter_content(65536):
            size+=len(chunk)
            if size>8*1024*1024 or time.monotonic()-started>20: raise ValueError()
            chunks.append(chunk)
        with Image.open(io.BytesIO(b''.join(chunks)),formats=['JPEG','PNG','WEBP']) as image:
            w,h=image.size
            if w*h>24000000 or max(w,h)/min(w,h)>20: raise ValueError()
            image.thumbnail((2000,2000))
            converted=image.convert('RGB');out=io.BytesIO();converted.save(out,format='JPEG',quality=85)
            return post,out.getvalue()
    except (requests.RequestException,ValueError,OSError,Image.DecompressionBombError):
        # This fallback precedes the reservation and the only Telegram POST.
        body={k:v for k,v in post['body'].items() if k not in ('photo','caption')}
        body['text']=post['body']['caption'];body['link_preview_options']={'is_disabled':True}
        return {**post,'method':'sendMessage','body':body},None
    finally:
        if response is not None: response.close()

class StateClient:
    def __init__(self,base,token,session=None):
        self.base=origin(base);self.token=token;self.session=session or requests.Session()
        if len(token)<32: raise PublishError('Configure MIRA_SOCIAL_WRITE_TOKEN com pelo menos 32 caracteres')
    def call(self,action,body):
        try:
            response=self.session.post(self.base+'/api/social/'+action,json=body,
                headers={'Authorization':'Bearer '+self.token},timeout=(5,20),allow_redirects=False)
            data=response.json()
            if response.status_code!=200 or not isinstance(data,dict): raise ValueError()
            return data
        except (requests.RequestException,ValueError): raise PublishError('Estado remoto indisponível; não repetir envio sem conferir o registro') from None

class TelegramClient:
    def __init__(self,token,session=None):
        if not re.fullmatch(r'\d{5,}:[A-Za-z0-9_-]{20,}',token): raise PublishError('Configure TELEGRAM_BOT_TOKEN')
        self.base='https://api.telegram.org/bot'+token;self.session=session or requests.Session()
    def read(self,method,params):
        try:
            r=self.session.get(self.base+'/'+method,params=params,timeout=(5,20),allow_redirects=False);data=r.json()
            if r.status_code!=200 or not isinstance(data,dict) or data.get('ok') is not True or not isinstance(data.get('result'),dict): raise ValueError()
            return data['result']
        except (requests.RequestException,ValueError,KeyError,AttributeError): raise PublishError('Não foi possível validar bot/canal no Telegram') from None
    def preflight(self,chat):
        me=self.read('getMe',{});channel=self.read('getChat',{'chat_id':chat})
        if me.get('is_bot') is not True or channel.get('type')!='channel' or not isinstance(channel.get('id'),int):
            raise PublishError('Destino precisa ser um canal Telegram')
        member=self.read('getChatMember',{'chat_id':channel['id'],'user_id':me['id']})
        if member.get('status')!='administrator' or member.get('can_post_messages') is not True:
            raise PublishError('Bot precisa ser administrador com permissão de publicar')
        return channel['id']
    def send(self,method,body,chat,photo=None):
        try:
            if photo is not None:
                fields={k:(json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v) for k,v in body.items() if k!='photo'}
                fields['chat_id']=str(chat)
                r=self.session.post(self.base+'/'+method,data=fields,files={'photo':('offer.jpg',photo,'image/jpeg')},timeout=(5,30),allow_redirects=False)
            else:
                r=self.session.post(self.base+'/'+method,json={**body,'chat_id':chat},timeout=(5,30),allow_redirects=False)
            data=r.json()
        except (requests.RequestException,ValueError): return {'status':'uncertain'}
        result=data.get('result') if isinstance(data,dict) else None
        if r.status_code==200 and data.get('ok') is True and isinstance(result,dict):
            mid=result.get('message_id');chat_result=result.get('chat');cid=chat_result.get('id') if isinstance(chat_result,dict) else None
            if isinstance(mid,int) and not isinstance(mid,bool) and mid>0 and cid==chat:
                return {'status':'sent','messageId':mid}
        # Only a well-formed, explicit Telegram rejection is definitive.
        if isinstance(data,dict) and data.get('ok') is False and data.get('error_code')==r.status_code and 400<=r.status_code<500:
            return {'status':'rejected'}
        return {'status':'uncertain'}

def verify_redirect(post,entry,session):
    expected=entry['baseUrl']+entry['search']+entry['hash']
    try:
        r=session.get(post['link'],allow_redirects=False,timeout=(5,15))
        if r.status_code!=302 or r.headers.get('Location')!=expected: raise ValueError()
    except (requests.RequestException,ValueError): raise PublishError('Rota /go não corresponde ao destino afiliado registrado') from None

def publish(post,state,telegram,chat,entry,session=None):
    canonical=telegram.preflight(chat)
    network=session or requests.Session()
    verify_redirect(post,entry,network)
    post,photo=prepare_photo(post,network)
    channel=hashlib.sha256(str(canonical).encode()).hexdigest()
    claim=state.call('claim',{'channel':channel,'fingerprint':post['fingerprint']})
    if claim.get('claimed') is not True: return {'posted':False,'reason':claim.get('reason'),'reservation':claim.get('id')}
    rid=claim.get('id')
    if not isinstance(rid,str) or not rid: raise PublishError('Reserva inválida; envio cancelado')
    receipt=telegram.send(post['method'],post['body'],canonical,photo=photo) if photo is not None else telegram.send(post['method'],post['body'],canonical)
    # Persisted reservation survives crashes and failures while saving this receipt.
    saved=state.call('finish',{'channel':channel,'id':rid,**receipt})
    if saved.get('saved') is not True: raise PublishError('Recibo não confirmado; conferir reserva '+rid)
    if receipt['status']!='sent': raise PublishError('Telegram '+receipt['status']+'; reserva '+rid+'; conferir antes de qualquer nova tentativa')
    return {'posted':True,'productId':post['productId'],'messageId':receipt['messageId'],'reservation':rid}

def run(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run',action='store_true')
    parser.add_argument('--check',action='store_true',help='Valida bot, canal e /go sem reservar ou enviar')
    parser.add_argument('--text-only',action='store_true')
    parser.add_argument('--status',action='store_true')
    parser.add_argument('--resolve',metavar='RESERVATION_ID')
    parser.add_argument('--outcome',choices=['sent','rejected'])
    parser.add_argument('--message-id',type=int)
    args=parser.parse_args(argv)
    from integracoes.social.gerar_pauta import load_catalog,load_radar
    if args.status or args.resolve:
        state=StateClient(os.environ.get('MIRA_SOCIAL_BASE_URL',''),os.environ.get('MIRA_SOCIAL_WRITE_TOKEN',''))
        telegram=TelegramClient(os.environ.get('TELEGRAM_BOT_TOKEN',''))
        cid=telegram.preflight(os.environ.get('TELEGRAM_CHAT_ID',''))
        channel=hashlib.sha256(str(cid).encode()).hexdigest()
        if args.resolve:
            if not args.outcome or (args.outcome=='sent' and (not args.message_id or args.message_id<=0)):
                raise PublishError('Informe --outcome e, para sent, --message-id')
            output=state.call('finish',{'channel':channel,'id':args.resolve,'status':args.outcome,'messageId':args.message_id})
        else: output=state.call('status',{'channel':channel})
        print(json.dumps(output));return output
    registry=json.loads((ROOT/'integracoes/cloudflare/affiliate-links.json').read_text())
    if args.check:
        telegram=TelegramClient(os.environ.get('TELEGRAM_BOT_TOKEN',''))
        telegram.preflight(os.environ.get('TELEGRAM_CHAT_ID',''))
        i=next(iter(registry))
        verify_redirect({'link':origin(os.environ.get('MIRA_GO_BASE_URL',''))+'/go/'+i},registry[i],requests.Session())
        output={'checked':True,'posted':False,'checkedRedirectId':i};print(json.dumps(output));return output
    selected=select_offer(load_catalog().get('products',[]),load_radar(),registry,datetime.now(timezone.utc))
    if not selected:
        output={'posted':False,'reason':'no_fresh_actionable_offer'};print(json.dumps(output));return output
    p,r=selected;post=build_post(p,r,os.environ.get('MIRA_GO_BASE_URL',''),args.text_only or os.environ.get('TELEGRAM_TEXT_ONLY')=='true')
    if args.dry_run:
        output={'dryRun':True,'productId':p['id'],'method':post['method'],'payload':post['body']};print(json.dumps(output,ensure_ascii=False));return output
    telegram=TelegramClient(os.environ.get('TELEGRAM_BOT_TOKEN',''));chat=os.environ.get('TELEGRAM_CHAT_ID','')
    if not re.fullmatch(r'(?:-100\d+|@[A-Za-z][A-Za-z0-9_]{4,})',chat): raise PublishError('Configure TELEGRAM_CHAT_ID do canal')
    state=StateClient(os.environ.get('MIRA_SOCIAL_BASE_URL',''),os.environ.get('MIRA_SOCIAL_WRITE_TOKEN',''))
    output=publish(post,state,telegram,chat,registry[p['id']])
    print(json.dumps(output));return output
