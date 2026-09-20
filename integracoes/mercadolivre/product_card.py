"""Read an exact product card from public HTML; never infer a price by proximity."""
from dataclasses import dataclass, field
from decimal import Decimal
from html.parser import HTMLParser
import re
from urllib.parse import parse_qs, unquote, urlsplit


class Unconfirmed(ValueError):
    pass


@dataclass
class Node:
    tag: str
    attrs: dict = field(default_factory=dict)
    children: list = field(default_factory=list)
    closed: bool = False

    def has(self, name):
        return name in self.attrs.get('class', '').split()

    def text(self):
        return ''.join(c.text() if isinstance(c, Node) else c for c in self.children)

    def find(self, name):
        found = []
        for child in self.children:
            if isinstance(child, Node):
                if child.has(name): found.append(child)
                found.extend(child.find(name))
        return found


class Cards(HTMLParser):
    VOID = {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node('root')
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, dict(attrs), closed=tag in self.VOID)
        self.stack[-1].children.append(node)
        if tag not in self.VOID: self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID: self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1, 0, -1):
            if self.stack[i].tag == tag:
                # An unclosed inner element makes its ancestors incomplete.
                self.stack[i].closed = i == len(self.stack)-1
                del self.stack[i:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def identity(url):
    """Only item IDs in product path/explicit parameters count, not tracking text."""
    parsed = urlsplit(url)
    host = parsed.hostname or ''
    if parsed.scheme != 'https' or not (host == 'mercadolivre.com.br' or host.endswith('.mercadolivre.com.br')):
        raise Unconfirmed('unexpected_product_host')
    # /p/MLB... is a catalog product, not the seller's item ID.
    path_item = re.match(r'^/MLB-(\d{7,})(?:-|/|$)', unquote(parsed.path), re.I)
    ids = {path_item[1]} if path_item else set()
    variation = set()
    params = parse_qs(parsed.query)
    fragment = parse_qs(parsed.fragment)
    for source in (params, fragment):
        for key in ('wid','item_id','pdp_filters'):
            for value in source.get(key, []):
                if key == 'pdp_filters':
                    ids.update(re.findall(r'(?:^|[|,])item_id:MLB-?(\d{7,})(?:$|[|,])', value, re.I))
                else:
                    match = re.fullmatch(r'MLB-?(\d{7,})', value, re.I)
                    if match: ids.add(match[1])
        for key in ('searchVariation','variation_id'):
            for value in source.get(key, []):
                if not value.isdigit(): raise Unconfirmed('invalid_variation')
                variation.add(value)
    if len(ids) != 1 or len(variation) > 1:
        raise Unconfirmed('ambiguous_product_identity')
    return 'MLB' + next(iter(ids)), next(iter(variation), None)


def amount(node):
    money = node.find('andes-money-amount')
    if node.has('andes-money-amount'): money.insert(0, node)
    if len(money) != 1: raise Unconfirmed('ambiguous_amount')
    money = money[0]
    fraction = money.find('andes-money-amount__fraction')
    cents = money.find('andes-money-amount__cents')
    currency = money.find('andes-money-amount__currency-symbol')
    if len(currency) != 1 or currency[0].text().strip() != 'R$':
        raise Unconfirmed('unconfirmed_currency')
    if len(fraction) != 1 or len(cents) > 1: raise Unconfirmed('ambiguous_amount')
    whole = fraction[0].text().strip()
    decimals = cents[0].text().strip() if cents else '00'
    if not re.fullmatch(r'(?:\d+|\d{1,3}(?:\.\d{3})+)', whole) or not re.fullmatch(r'\d{2}', decimals):
        raise Unconfirmed('invalid_amount')
    value = Decimal(whole.replace('.','') + '.' + decimals)
    if not 0 < value < 10_000_000: raise Unconfirmed('invalid_amount')
    return float(value)


def extract(body, item_id, reference_url):
    expected_id, expected_variation = identity(reference_url)
    if expected_id != item_id: raise Unconfirmed('reference_id_mismatch')
    parser = Cards()
    parser.feed(body)
    parser.close()
    results = []
    for card in parser.root.find('poly-card'):
        titles = card.find('poly-component__title')
        if len(titles) != 1 or titles[0].tag != 'a': continue
        try:
            found_id, variation = identity(titles[0].attrs.get('href',''))
        except Unconfirmed:
            continue
        if found_id != item_id: continue
        if not card.closed or card.find('poly-card'):
            raise Unconfirmed('incomplete_product_card')
        # If a specific variation was registered, an unspecified one cannot confirm it.
        if expected_variation is not None and variation != expected_variation:
            raise Unconfirmed('variation_mismatch')
        price_blocks = card.find('poly-component__price')
        if len(price_blocks) != 1: raise Unconfirmed('ambiguous_price_block')
        block = price_blocks[0]
        if re.search(r'cupom|primeira compra|a partir|assinant|meli\+|\bpix\b|cart[aã]o', block.text(), re.I):
            raise Unconfirmed('conditional_price_requires_review')
        current = block.find('poly-price__current')
        if len(current) != 1: raise Unconfirmed('current_price_not_found')
        price = amount(current[0])
        previous = block.find('andes-money-amount--previous')
        old = None
        if len(previous) == 1:
            try: old = amount(previous[0])
            except Unconfirmed: pass
        if old is not None and old <= price: old = None
        results.append((price, old, variation))
    if not results: raise Unconfirmed('exact_product_card_not_found')
    if len(set(results)) != 1: raise Unconfirmed('conflicting_product_cards')
    price, old, variation = results[0]
    return {'price':price, 'oldPrice':old, 'variationId':variation, 'currency':'BRL'}
