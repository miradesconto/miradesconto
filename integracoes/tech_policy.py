"""Política editorial tech compartilhada por geração e sincronização."""
import math
import re
import unicodedata

CATEGORIES = ('PC e hardware', 'Notebooks', 'Celulares', 'Setup', 'Gaming', 'Áudio', 'Smart Home', 'TVs e projetores', 'Impressoras')

def category(product):
    text = unicodedata.normalize('NFKD', product.get('name', '')).encode('ascii', 'ignore').decode().lower()
    # Evita classificar itens de outros nichos por uma palavra incidental.
    if re.search(r'pressao arterial|brinquedo|infantil|barbie|musculacao|academia|parafusadeira|carro eletrico|astronauta|sino de mesa|mochila|chroma key|bobinas|globo|bts army|fumaca|monoculo|visao noturna 1080', text):
        return None
    for pattern, label in (
        (r'^controle.*(?:ps4|ps5|xbox)', 'Gaming'),
        (r'^kit de gravacao|kit chave precisao', 'Setup'),
        (r'fone|headset|microfone|vitrola|caixa de som', 'Áudio'),
        (r'camera|fechadura digital|campainha|smart tag|smart home', 'Smart Home'),
        (r'projetor|smart tv|televisor', 'TVs e projetores'),
        (r'impressora|caneta 3d', 'Impressoras'),
        (r'controle.*(?:ps4|ps5|xbox)|playstation|nintendo|borderlands|grip|analogico|cooler dobe', 'Gaming'),
        (r'power bank|carregador|iphone|smartphone|suporte.*(?:celular|tablet)|lente celular|smartwatch', 'Celulares'),
        (r'mouse|teclado|monitor gamer|ring light|kit de gravacao|passador slide|kit chave precisao', 'Setup'),
        (r'modem|roteador|fibra optica|placa de video|processador|memoria ram|placa.mae|\bssd\b|gabinete gamer', 'PC e hardware'),
        (r'^notebook|^laptop', 'Notebooks'),
    ):
        if re.search(pattern, text):
            return label
    return None

def eligible(product):
    evidence = product.get('priceCheck') or {}
    price, old = product.get('price'), product.get('oldPrice')
    return bool(category(product) and product.get('available') is not False
        and all(isinstance(n, (int, float)) and not isinstance(n, bool) and math.isfinite(n) for n in (price, old))
        and 0 < price < old and evidence.get('status') == 'verified'
        and evidence.get('price') == price and evidence.get('oldPrice') == old
        and evidence.get('currency') == 'BRL')

def reconcile(catalog):
    if catalog.get('metadata', {}).get('niche') != 'tech':
        return catalog
    rows = {p['id']: p for p in catalog['products']}
    ordered = catalog['publishedIds']
    ids = [i for i in ordered if eligible(rows[i])]
    catalog['publishedIds'] = ids
    positions = {item: rank for rank, item in enumerate(ids, 1)}
    for p in catalog['products']:
        label = category(p)
        if label:
            p['category'] = label
        rank = positions.get(p['id'])
        if rank is not None:
            p['rank'] = rank
        p['featured'] = rank is not None and rank <= 12
    return catalog
