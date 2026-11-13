"""Publica somente as cinco artes aprovadas em 13/11/2026."""
import base64,json,os,subprocess
from pathlib import Path
from urllib.request import urlopen,Request
from api import pinterest_request,find_existing_pin
from publicar_lote import find_board
ROOT=Path(__file__).resolve().parents[2]
CFG=ROOT/'integracoes/pinterest/lote_setup_20261113.json'
STATE=ROOT/'integracoes/pinterest/estado_setup_20261113.json'
def save(state):
    STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
    subprocess.run(['git','add',str(STATE.relative_to(ROOT))],check=True)
    subprocess.run(['git','commit','-m','Registra publicação dos pins setup 13/11'],check=True)
    subprocess.run(['git','push','origin','HEAD:main'],check=True)
def main():
    if os.getenv('GITHUB_REF')!='refs/heads/main': raise RuntimeError('Somente main')
    token=os.environ['PINTEREST_ACCESS_TOKEN']
    posts=json.loads(CFG.read_text())
    if len(posts)!=5: raise RuntimeError('Esperadas cinco artes')
    state=json.loads(STATE.read_text()) if STATE.exists() else {}
    if any(p.get('status')=='uncertain' for p in state.values()):
        raise RuntimeError('Envio incerto anterior: reconciliar manualmente antes de repetir')
    board=find_board(token,'Ofertas de Tecnologia e Achadinhos | MiraDesconto')
    arts={}
    for p in posts:
        if not p['link'].startswith('https://miradesconto.com.br/'): raise ValueError('Destino inválido')
        with urlopen(Request(p['link'],headers={'User-Agent':'Mozilla/5.0'}),timeout=30) as r:
            if r.status!=200: raise RuntimeError('Destino indisponível')
        data=(ROOT/p['image']).read_bytes()
        if not data.startswith(b'\xff\xd8') or len(data)<20000: raise ValueError('Arte inválida')
        arts[p['key']]=base64.b64encode(data).decode()
    for p in posts:
        key=p['key']
        if state.get(key,{}).get('status')=='published':
            print('JÁ PUBLICADO',key,state[key]['pinId'],flush=True);continue
        existing=find_existing_pin(token,p['link'])
        if existing:
            state[key]={'status':'published','pinId':str(existing),'link':p['link']}
            save(state)
            print('EXISTENTE',key,existing,flush=True);continue
        state[key]={'status':'uncertain','link':p['link']}
        save(state)
        result=pinterest_request(token,'/pins',{
            'board_id':board,'title':p['title'],'description':p['description'],
            'link':p['link'],'alt_text':p['title']+' — arte ilustrativa MiraDesconto branca e verde.',
            'media_source':{'source_type':'image_base64','content_type':'image/jpeg','data':arts[key],'is_standard':True}})
        pin_id=str(result.get('id',''))
        if not pin_id.isdigit(): raise RuntimeError('Resposta incerta; não repetir')
        state[key]['pinId']=pin_id
        save(state)
        check=pinterest_request(token,'/pins/'+pin_id)
        if check.get('link')!=p['link'] or str(check.get('board_id'))!=board:
            raise RuntimeError('Verificação falhou')
        state[key]={'status':'published','pinId':pin_id,'link':p['link']}
        save(state)
        print('PUBLICADO E VERIFICADO',key,'https://www.pinterest.com/pin/'+pin_id+'/',flush=True)
if __name__=='__main__': main()
