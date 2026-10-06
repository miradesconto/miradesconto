"""Cadastro por link oficial: identidade exata, metadados e preço confirmado."""
import copy
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'integracoes'))
from product_card import identity, Cards, Node, Unconfirmed, extract
from rebuild_catalog import refresh_one
from hourly_prices import Client, observe
from tech_policy import category, reconcile
import catalogo


def allowed(url):
    p = urlsplit(url)
    host = p.hostname or ''
    return (p.scheme == 'https' and not p.username and not p.password
            and p.port in (None, 443) and (host in ('meli.la', 'mercadolivre.com', 'mercadolivre.com.br')
            or host.endswith('.mercadolivre.com.br')))


def affiliate(url):
    return bool(re.fullmatch(r'https://(?:meli\.la/[A-Za-z0-9]+|(?:www\.)?mercadolivre\.com(?:\.br)?/sec/[A-Za-z0-9]+)', url))


class Redirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not allowed(newurl):
            raise ValueError('Redirecionamento fora do Mercado Livre')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Metadata(HTMLParser):
    def __init__(self):
        super().__init__()
        self.values = {}
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta':
            key = attrs.get('property') or attrs.get('name')
            if key in ('og:title', 'og:image'):
                self.values[key] = attrs.get('content', '')


def resolve(link):
    if not affiliate(link):
        raise ValueError('Use um link oficial meli.la ou Mercado Livre /sec/')
    opener = build_opener(Redirects())
    with opener.open(Request(link, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'text/html'}), timeout=30) as response:
        final = response.geturl()
        destination = urlsplit(final)
        print('Destino do link:', destination.scheme + '://' + destination.netloc + destination.path)
        if not allowed(final):
            raise ValueError('Destino inesperado')
        body = response.read(3_000_001)
    if len(body) > 3_000_000:
        raise ValueError('Página grande demais; cadastro exige revisão')
    return parse_page(body.decode('utf-8', errors='replace'), final, link)


def parse_page(body, final, link):
    # Affiliate landing pages carry the actual listing in a product card.
    # Never choose the first item from a list or infer an ID from tracking text.
    observation = None
    try:
        item_id, variation = identity(final)
        product_url = final
        parser = Metadata()
        parser.feed(body)
        name = parser.values.get('og:title', '').strip()
        image = parser.values.get('og:image', '')
    except Unconfirmed:
        cards = Cards()
        cards.feed(body)
        cards.close()
        candidates = {}
        print('Cartões encontrados:', len(cards.root.find('poly-card')))
        for card in cards.root.find('poly-card'):
            titles = card.find('poly-component__title')
            if len(titles) != 1 or titles[0].tag != 'a':
                continue
            url = titles[0].attrs.get('href', '')
            try:
                found_id, found_variation = identity(url)
            except Unconfirmed:
                continue
            def images(node):
                found = []
                if node.tag == 'img':
                    found.append(node.attrs.get('data-src') or node.attrs.get('src') or '')
                for child in node.children:
                    if isinstance(child, Node):
                        found.extend(images(child))
                return found
            image_urls = [u for u in images(card) if urlsplit(u).scheme == 'https'
                          and (urlsplit(u).hostname or '').endswith('.mlstatic.com')]
            if len(set(image_urls)) != 1:
                continue
            key = (found_id, found_variation)
            value = (url, titles[0].text().strip(), image_urls[0])
            if key in candidates and candidates[key] != value:
                raise ValueError('Cartões divergentes; revisão necessária')
            candidates[key] = value
        # A named list with one product is still a list, not an individual link.
        if len(candidates) > 1 or '/lists/' in urlsplit(final).path:
            rows = []
            for (found_id, found_variation), (url, title, picture) in candidates.items():
                row = dict(id=found_id, itemId=found_id, name=title, imageUrl=picture,
                           affiliateUrl=link, productUrl=url, featured=False)
                label = category(row)
                if not label or found_variation:
                    continue
                try:
                    row['_observation'] = extract(body, found_id, url)
                except Unconfirmed:
                    continue
                row['category'] = label
                rows.append(row)
            if not rows:
                raise ValueError('Lista sem produtos tech com cartão exato confirmado')
            print('Produtos tech confirmados na lista:', len(rows))
            return rows
        if len(candidates) != 1:
            raise ValueError('Página sem anúncio identificável e imagem confirmada')
        (item_id, variation), (product_url, name, image) = next(iter(candidates.items()))
        observation = extract(body, item_id, product_url)
    ip = urlsplit(image)
    if not name or len(name) > 300 or ip.scheme != 'https' or not (ip.hostname or '').endswith('.mlstatic.com'):
        raise ValueError('Título/imagem não confirmados; página pode estar bloqueada')
    result = dict(id=item_id, itemId=item_id, name=name, imageUrl=image,
                  affiliateUrl=link, productUrl=product_url, featured=False)
    if variation:
        raise ValueError('Produto com variação exige revisão manual antes do cadastro')
    label = category(result)
    if not label:
        raise ValueError('Produto não reconhecido como tech; revisar categoria')
    result['category'] = label
    if observation:
        result['_observation'] = observation
    return result


def prepare(current, archive, links, now, resolver=resolve, verifier=None):
    if not links or len(links) > 20:
        raise ValueError('Envie de 1 a 20 links')
    updated, approved = copy.deepcopy(current), copy.deepcopy(archive)
    ids = {p['id'] for p in updated['products']}
    resolved = []
    for link in dict.fromkeys(links):
        candidate = resolver(link)
        rows = candidate if isinstance(candidate, list) else [candidate]
        resolved.extend((link, row, isinstance(candidate, list)) for row in rows)
        if isinstance(candidate, list):
            sources = updated['metadata'].setdefault('affiliateSources', [])
            if link not in sources:
                sources.append(link)
    for link, candidate, from_list in resolved:
        if candidate['id'] in ids:
            if from_list:
                continue
            raise ValueError('Produto já cadastrado: ' + candidate['id'])
        candidate['rank'] = len(updated['products']) + 1
        candidate['registrationSource'] = 'affiliate-panel'
        observation = candidate.pop('_observation', None)
        verified = None
        if observation:
            price, old = observation['price'], observation['oldPrice']
            discount = round((1 - price / old) * 100, 4) if old else None
            verified = dict(candidate, price=price, oldPrice=old, discount=discount,
                displayedDiscount=f'{round(discount)}% OFF' if discount else None,
                available=None, availabilityStatus='unknown', priceSource='poly-card-v1',
                collectedAt=now.strftime('%d/%m/%Y'),
                priceCheck=dict(status='verified', method='poly-card-v1',
                    itemId=candidate['id'], variationId=None, currency='BRL',
                    checkedAt=now.isoformat(timespec='seconds'), price=price, oldPrice=old))
        elif verifier:
            verified = verifier(candidate, now)
        if verified is None:
            verified, error = refresh_one(candidate, now.isoformat(timespec='seconds'))
            if verified is None:
                raise ValueError('Preço não confirmado: ' + str((error or {}).get('reason')))
        updated['products'].append(verified)
        # Sem promoção fica registrado, mas fora da vitrine.
        updated['publishedIds'].append(candidate['id'])
        approved.append(dict(id=candidate['id'], affiliateUrl=link,
                             productUrl=candidate['productUrl'], generatedAt=now.date().isoformat()))
        ids.add(candidate['id'])
    reconcile(updated)
    return updated, approved


def configured_sources(current, source_file):
    # The editable list configuration replaces previous discovery sources.
    # Existing product affiliate links remain registered and unchanged.
    links = (catalogo.read_json(source_file)['links'] if source_file.exists()
             else current['metadata'].get('affiliateSources', []))
    links = list(dict.fromkeys(links))
    if any(not affiliate(link) for link in links):
        raise ValueError('Lista configurada sem link oficial de afiliado')
    return links


def main():
    syncing = '--sync' in sys.argv
    current = catalogo.load(ROOT)
    links = current['metadata'].get('affiliateSources', []) if syncing else os.environ.get('AFFILIATE_LINKS', '').split()
    source_file = ROOT / 'integracoes/mercadolivre/listas-afiliadas.json'
    if syncing:
        links = configured_sources(current, source_file)
    if syncing and not links:
        print('Sem listas cadastradas para descobrir novos produtos')
        return
    if not links:
        links = catalogo.read_json(ROOT / 'integracoes/mercadolivre/cadastro-pendente.json')['links']
    client = None
    try:
        client = Client()
    except RuntimeError:
        print('API não configurada; confirmação por cartão público exato')
    def verify(candidate, now):
        if client:
            try:
                return observe(candidate, client, now)
            except (RuntimeError, ValueError):
                print('API sem confirmação; tentando cartão público exato')
        return None
    archive = catalogo.read_json(ROOT / 'links-afiliados.json')
    if syncing:
        updated = copy.deepcopy(current)
        updated['metadata']['affiliateSources'] = links
        for link in links:
            try:
                updated, archive = prepare(updated, archive, [link], datetime.now(timezone.utc), verifier=verify)
            except Exception as exc:
                print('Lista preservada sem importar novos itens:', str(exc))
    else:
        updated, archive = prepare(current, archive, links, datetime.now(timezone.utc), verifier=verify)
    if updated == current:
        print('Nenhum novo produto; catálogo preservado')
        return
    with tempfile.TemporaryDirectory() as tmp:
        check = Path(tmp)
        (check / 'links-afiliados.json').write_text(catalogo.dumps(archive), encoding='utf-8')
        files = catalogo.render(updated, check)
    files['links-afiliados.json'] = catalogo.dumps(archive, pretty=True) + '\n'
    files[catalogo.SOURCE.as_posix()] = catalogo.dumps(updated, pretty=True) + '\n'
    catalogo.write_files(files, ROOT)
    print('Cadastro confirmado. Produtos sem desconto ficam fora da vitrine.')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('Cadastro não publicado: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
