"""Uso: python atualizar_produtos.py MiraDesconto_ofertas_revisadas.xlsx
Lê XLSX com a biblioteca padrão do Python, sem instalar pacotes.
Também gera catalogo-seo.json: índice leve para marketing, SEO e automações.
"""
import sys, json, re, math, zipfile, unicodedata
from pathlib import Path
from urllib.parse import urlparse, unquote
import xml.etree.ElementTree as ET

NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
def read_xlsx(path):
    with zipfile.ZipFile(path) as z:
        strings = []
        if 'xl/sharedStrings.xml' in z.namelist():
            strings = [''.join(e.itertext()) for e in ET.fromstring(z.read('xl/sharedStrings.xml'))]
        rels = {e.attrib['Id']: e.attrib['Target'] for e in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
        result = {}
        for s in ET.fromstring(z.read('xl/workbook.xml')).find('m:sheets', NS):
            rid = s.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']
            target = rels[rid]
            target = target.lstrip('/') if target.startswith('/') else 'xl/' + target
            rows = []
            for row in ET.fromstring(z.read(target)).findall('m:sheetData/m:row', NS):
                cells = {}
                for c in row:
                    col = re.sub(r'\d', '', c.attrib['r'])
                    v = c.find('m:v', NS)
                    t = c.attrib.get('t')
                    if t == 'inlineStr': value = ''.join(c.find('m:is', NS).itertext())
                    elif v is None or v.text is None: continue
                    elif t == 's': value = strings[int(v.text)]
                    elif t in ('str','e'): value = v.text
                    else:
                        try: value = float(v.text)
                        except ValueError: value = v.text
                    cells[col] = value
                if cells: rows.append((int(row.attrib['r']), cells))
            result[s.attrib['name']] = rows
        return result

def normalized(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c) != 'Mn')

ORGANIZATION = json.loads((Path(__file__).resolve().parent/'organizacao-catalogo.json').read_text(encoding='utf-8'))

def category(name, pid=None):
    override = ORGANIZATION['overrides'].get(pid)
    if override:
        return override
    n = normalized(name)
    return next((rule['category'] for rule in ORGANIZATION['rules'] if re.search(rule['pattern'], n)), 'Outros')

def url_ok(s):
    try: return isinstance(s,str) and urlparse(s).scheme in ('http','https') and bool(urlparse(s).hostname) and not re.search(r'[\s<>"\x00-\x1f]',s)
    except ValueError: return False
def number(v): return isinstance(v,(float,int)) and not isinstance(v,bool) and math.isfinite(v) and v > 0

def write_marketing_catalog(products, out, collected_at):
    """Gera índice compacto sem alterar os dados usados pela vitrine."""
    items = []
    for p in products:
        if not p.get('affiliateUrl'):
            continue
        items.append({
            'id': p['id'],
            'name': p['name'],
            'category': p['category'],
            'featured': p.get('featured', False),
            'price': p['price'],
            'oldPrice': p['oldPrice'],
            'discount': p['discount'],
            'affiliateUrl': p['affiliateUrl'],
            'imageUrl': p.get('imageUrl'),
            'rank': p['rank']
        })
    payload = {
        'generatedFrom': 'produtos.js',
        'collectedAt': collected_at,
        'count': len(items),
        'products': items
    }
    (out/'catalogo-seo.json').write_text(
        json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(',', ':')),
        encoding='utf-8'
    )

def write_catalog_chunks(products, out):
    """Exporta o catálogo em lotes de até 100 produtos, na ordem da vitrine."""
    catalog_dir = out/'catalogo'
    catalog_dir.mkdir(parents=True, exist_ok=True)
    fields = ('id', 'name', 'category', 'price', 'oldPrice', 'discount',
              'affiliateUrl', 'imageUrl', 'rank', 'featured')
    generated = set()
    for start in range(0, len(products), 100):
        filename = f'produtos-{start // 100 + 1:03d}.json'
        batch = [{key: product[key] for key in fields}
                 for product in products[start:start + 100]]
        (catalog_dir/filename).write_text(
            json.dumps(batch, ensure_ascii=False, allow_nan=False, separators=(',', ':')) + '\n',
            encoding='utf-8')
        generated.add(filename)
    for old_file in catalog_dir.glob('produtos-*.json'):
        if old_file.name not in generated:
            old_file.unlink()

def convert(path, out):
    sheets = read_xlsx(path)
    affiliate = {c.get('K'): c['L'] for _,c in sheets.get('Escolher ofertas',[]) if url_ok(c.get('L'))}
    ranks = {c.get('B'): i for i,(_,c) in enumerate(sheets.get('Ranking',[])) if c.get('B')}
    date = next((c.get('B') for _,c in sheets.get('Leia-me',[]) if c.get('A') == 'Data da coleta'), None)
    products, rejected, seen = [], [], set()
    for row,c in sheets['Produtos']:
        if row == 1: continue
        name, pid, price, url = c.get('A'), c.get('B'), c.get('C'), c.get('K')
        reasons = []
        if not isinstance(name,str) or not name.strip(): reasons.append('Produto ausente')
        if not number(price): reasons.append('Preço inválido')
        if not url_ok(url): reasons.append('URL inválida')
        if not isinstance(pid,str) or not re.fullmatch(r'MLB\d+',pid): reasons.append('ID inválido')
        elif url_ok(url) and pid[3:] not in unquote(url): reasons.append('ID não encontrado na URL')
        if pid in seen: reasons.append('ID duplicado')
        if reasons:
            rejected.append({'row':row,'id':pid,'reasons':reasons}); continue
        seen.add(pid)
        old = c.get('D') if number(c.get('D')) else None
        discount = round((1-price/old)*100,4) if old and old > price else None
        products.append(dict(id=pid,name=name,price=price,oldPrice=old,discount=discount,
            displayedDiscount=c.get('E'),category=category(name,pid),categorySource='Organização por tipo de produto; regras e revisões em organizacao-catalogo.json',
            featured=pid in ORGANIZATION['featuredIds'],
            store='Mercado Livre',storeSource='Domínio da URL',productUrl=url,affiliateUrl=affiliate.get(url),
            imageUrl=None,commission=c.get('F'),extraEarnings=c.get('G'),rating=c.get('H'),salesText=c.get('I'),
            highlight=c.get('J'),priceEvidence=c.get('L'),installment=c.get('M'),collectedAt=date,
            source={'sheet':'Produtos','row':row},rank=ranks.get(pid,99999)))
    products.sort(key=lambda p:p['rank'])
    affiliate_file = out/'links-afiliados.json'
    if affiliate_file.exists():
        saved = {e['id']: e for e in json.loads(affiliate_file.read_text(encoding='utf-8'))}
        for product in products:
            entry = saved.get(product['id'], {})
            if entry.get('productUrl') == product['productUrl'] and url_ok(entry.get('affiliateUrl')):
                product['affiliateUrl'] = entry['affiliateUrl']
    image_file = out/'imagens-produtos.json'
    if image_file.exists():
        images = json.loads(image_file.read_text(encoding='utf-8'))
        for product in products:
            entry = images.get(product['id'], {})
            if url_ok(entry.get('imageUrl')):
                product['imageUrl'] = entry['imageUrl']
                product['imageSource'] = entry.get('sourceUrl')
    data = {'sourceFile':Path(path).name,'collectedAt':date,'products':products}
    out.mkdir(parents=True,exist_ok=True)
    (out/'produtos.js').write_text('// Gerado da planilha. Ausências permanecem null.\nwindow.MIRA_DATA = '+json.dumps(data,ensure_ascii=False,allow_nan=False,separators=(',',':'))+';\n',encoding='utf-8')
    write_marketing_catalog(products, out, date)
    write_catalog_chunks(products, out)
    stats = {'valid':len(products),'rejected':rejected,'missingOldPrice':sum(p['oldPrice'] is None for p in products),'displayedDiscount':sum(bool(p['displayedDiscount']) for p in products),'affiliateLinks':len(affiliate),'images':0,'categories':{c:sum(p['category']==c for p in products) for c in sorted(set(p['category'] for p in products))}}
    stats['images'] = sum(bool(p['imageUrl']) for p in products)
    stats['affiliateLinks'] = sum(bool(p['affiliateUrl']) for p in products)
    (out/'analise-dados.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(stats,ensure_ascii=False))
    return products
if __name__ == '__main__':
    if len(sys.argv)!=2: raise SystemExit('Uso: python atualizar_produtos.py arquivo.xlsx')
    convert(sys.argv[1],Path(__file__).resolve().parent)
