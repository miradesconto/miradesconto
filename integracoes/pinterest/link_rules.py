"""Regras de URLs e identificação comercial dos Pins de afiliados; sem acesso à rede."""
import re
from urllib.parse import urlsplit

ML_HOSTS = frozenset({
    'meli.la', 'mercadolivre.com.br', 'www.mercadolivre.com.br',
    'produto.mercadolivre.com.br',
})
DISCLOSURE = ('Conteúdo com link de afiliado; podemos receber comissão '
              'por compras elegíveis.')


def validate_ml_link(link):
    """Aceita somente HTTPS do Mercado Livre, nunca domínios parecidos ou URL arbitrária."""
    if (not isinstance(link, str) or not link or link != link.strip()
            or re.search(r'[\x00-\x20\x7f]', link)):
        raise ValueError('Link de afiliado inválido: não use espaços ou quebras de linha.')
    try:
        parsed = urlsplit(link)
        port = parsed.port
    except ValueError:
        raise ValueError('URL de afiliado malformada.') from None
    if (parsed.scheme != 'https' or parsed.hostname not in ML_HOSTS
            or parsed.username or parsed.password or port is not None
            or parsed.fragment):
        raise ValueError('Destino precisa ser HTTPS do Mercado Livre, sem redirecionador externo.')
    if parsed.hostname == 'meli.la':
        # Encurtador oficial do Mercado Livre; a aceitação final depende do Pinterest.
        if not re.fullmatch(r'/[A-Za-z0-9]{5,40}/?', parsed.path) or parsed.query:
            raise ValueError('Link meli.la fora do formato oficial esperado.')
    elif not parsed.path or parsed.path == '/':
        raise ValueError('Use o link do produto, não a página inicial do Mercado Livre.')
    return link


def affiliate_description(caption):
    """Texto útil + identificação comercial explícita, para ambos os fluxos."""
    if (not isinstance(caption, str) or caption != caption.strip()
            or re.search(r'[\x00-\x1f\x7f]', caption)
            or not 20 <= len(caption) <= 300):
        raise ValueError('Escreva uma legenda informativa de 20 a 300 caracteres, em uma linha.')
    return caption.rstrip(' .') + '. ' + DISCLOSURE
