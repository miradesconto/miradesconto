"""Preços oficiais, sem scraping, credenciais em disco ou alteração de afiliados."""
from __future__ import annotations

import copy
import json
import math
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'integracoes'))
import catalogo

API = 'https://api.mercadolibre.com'
METHOD = 'ml-sale-price-v1'
REQUIRED = ('CLIENT_ID', 'CLIENT_SECRET', 'ACCESS_TOKEN', 'REFRESH_TOKEN', 'GH_SECRETS_TOKEN')


class ApiError(RuntimeError):
    def __init__(self, status, category=None):
        self.status = status
        self.category = category
        super().__init__(f'API HTTP {status}; resposta omitida para proteger credenciais')


class AuthError(RuntimeError):
    pass


def request(path, token=None, form=None):
    headers = {'Accept': 'application/json', 'User-Agent': 'MiraDesconto-price-sync'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    body = None
    if form is not None:
        body = urlencode(form).encode()
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
    # Refresh tokens are single use: never blindly retry an ambiguous POST.
    attempts = 1 if form is not None else 4
    for attempt in range(attempts):
        try:
            with urlopen(Request(API + path, data=body, headers=headers), timeout=20) as response:
                result = json.load(response)
            if not isinstance(result, dict):
                raise ValueError('Resposta da API não é um objeto')
            return result
        except HTTPError as exc:
            status = exc.code
            retry = exc.headers.get('Retry-After')
            category = None
            if path == '/oauth/token':
                try:
                    error = json.loads(exc.read(8192))
                    detail = ' '.join(str(error.get(k, '')) for k in ('error', 'message', 'error_description')).lower()
                    category = next((key for key in (
                        'invalid_grant', 'invalid_client', 'redirect_uri',
                        'code_verifier', 'invalid_request', 'unauthorized_client',
                        'expired_code', 'invalid_code'
                    ) if key in detail), None)
                except (ValueError, TypeError, OSError):
                    pass
            exc.close()
            if status not in (429, 500, 502, 503, 504) or attempt == attempts - 1:
                raise ApiError(status, category) from None
            delay = 2 ** (attempt + 1)
            if retry:
                try:
                    delay = max(delay, float(retry))
                except ValueError:
                    try:
                        delay = max(delay, (parsedate_to_datetime(retry) - datetime.now(timezone.utc)).total_seconds())
                    except (ValueError, TypeError):
                        pass
            if delay > 60:
                raise ApiError(status, category) from None
            print(f'HTTP {status}; nova tentativa em {delay:.0f}s')
            time.sleep(delay)
        except (URLError, TimeoutError, OSError):
            if attempt == attempts - 1:
                raise RuntimeError('Falha de rede; nenhum corpo de resposta registrado') from None
            time.sleep(2 ** (attempt + 1))


def gh(args, value=None):
    env = dict(os.environ, GH_TOKEN=os.environ['GH_SECRETS_TOKEN'])
    try:
        result = subprocess.run(['gh', *args], input=value, text=True,
                                capture_output=True, env=env, timeout=45)
    except (OSError, subprocess.TimeoutExpired):
        raise AuthError('Não foi possível executar gh para persistir OAuth') from None
    if result.returncode:
        raise AuthError('GitHub Secrets inacessível: confira GH_SECRETS_TOKEN e permissão Secrets: write')
    return result.stdout


class Client:
    def __init__(self):
        missing = [key for key in REQUIRED if not os.getenv(key, '').strip()]
        if missing:
            raise AuthError('Secrets ausentes: ' + ', '.join(missing))
        self.token = os.environ['ACCESS_TOKEN']
        self.refreshed = False

    def refresh(self):
        if self.refreshed:
            raise AuthError('Token renovado recusado; refaça a autorização OAuth')
        repo = os.environ.get('GITHUB_REPOSITORY', '')
        if not re.fullmatch(r'[\w.-]+/[\w.-]+', repo):
            raise AuthError('GITHUB_REPOSITORY ausente ou inválido')
        # Check access before consuming the single-use refresh token.
        gh(['secret', 'list', '--repo', repo, '--json', 'name'])
        self.refreshed = True
        try:
            data = request('/oauth/token', form={
                'grant_type': 'refresh_token', 'client_id': os.environ['CLIENT_ID'],
                'client_secret': os.environ['CLIENT_SECRET'],
                'refresh_token': os.environ['REFRESH_TOKEN'],
            })
        except (RuntimeError, ValueError):
            raise AuthError('Renovação OAuth falhou; verifique CLIENT_ID/CLIENT_SECRET e gere um novo par de tokens se necessário') from None
        access, refresh = data.get('access_token'), data.get('refresh_token')
        if not isinstance(access, str) or not access or not isinstance(refresh, str) or not refresh:
            raise AuthError('OAuth retornou tokens incompletos')
        if os.getenv('GITHUB_ACTIONS') == 'true':
            for value in (access, refresh):
                escaped = value.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
                print('::add-mask::' + escaped, flush=True)
        # Save the new refresh token FIRST, immediately, even if collection later fails.
        for name, value in (('REFRESH_TOKEN', refresh), ('ACCESS_TOKEN', access)):
            for attempt in range(3):
                try:
                    gh(['secret', 'set', name, '--repo', repo], value)
                    break
                except AuthError:
                    if attempt == 2:
                        raise AuthError(f'Não foi possível salvar {name}; refaça OAuth antes da próxima execução') from None
                    time.sleep(2 ** (attempt + 1))
        self.token = access
        print('OAuth renovado e salvo nos GitHub Secrets')

    def get(self, path):
        try:
            return request(path, self.token)
        except ApiError as exc:
            if exc.status != 401:
                raise
        self.refresh()
        try:
            return request(path, self.token)
        except ApiError as exc:
            if exc.status == 401:
                raise AuthError('API recusou o token renovado') from None
            raise


def ml_id(value):
    if not isinstance(value, str) or not re.fullmatch(r'MLB\d{7,}', value):
        raise ValueError('Identificador MLB inválido')
    return value


def positive(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def observe(product, client, now):
    result = copy.deepcopy(product)
    catalog_id = product.get('catalogProductId')
    if not catalog_id:
        # Only an actual /p/ URL identifies a catalog product; never guess from digits.
        url = urlsplit(product.get('productUrl') or '')
        if url.hostname in ('www.mercadolivre.com.br', 'mercadolivre.com.br'):
            match = re.search(r'/p/(MLB\d{7,})(?:/|$)', url.path)
            catalog_id = match.group(1) if match else None
    item_id = product.get('itemId') or product.get('id')
    if catalog_id:
        catalog_id = ml_id(catalog_id)
        data = client.get('/products/' + catalog_id)
        winner = data.get('buy_box_winner')
        if data.get('id') != catalog_id or not isinstance(winner, dict) or not winner.get('item_id'):
            raise ValueError('Produto de catálogo sem vencedor confirmado; preço preservado')
        item_id = winner['item_id']
        result['catalogProductId'] = catalog_id
    item_id = ml_id(item_id)
    sale = client.get(f'/items/{item_id}/sale_price?context=channel_marketplace')
    price, old = sale.get('amount'), sale.get('regular_amount')
    if sale.get('currency_id') != 'BRL' or not positive(price):
        raise ValueError('Preço atual inválido ou moeda diferente de BRL')
    if old is not None and not positive(old):
        raise ValueError('Preço de referência inválido')
    price = round(price, 2)
    if price <= 0:
        raise ValueError('Preço arredondado inválido')
    old = round(old, 2) if old is not None and old > price else None
    discount = round((1 - price / old) * 100, 4) if old else None
    stamp = now.isoformat(timespec='seconds')
    result.update(price=price, oldPrice=old, discount=discount, itemId=item_id,
                  displayedDiscount=f'{round(discount)}% OFF' if discount else None,
                  available=None, availabilityStatus='unknown', priceSource=METHOD)
    evidence = dict(status='verified', method=METHOD, itemId=item_id, currency='BRL',
                    price=price, oldPrice=old)
    previous = product.get('priceCheck') or {}
    # No hourly timestamp-only commits. Renew evidence before its 24h expiry.
    same = all(previous.get(k) == v for k, v in evidence.items()) and result == product
    if same:
        try:
            age = (now - datetime.fromisoformat(previous['checkedAt'])).total_seconds()
            if 0 <= age < 12 * 3600:
                return result
        except (KeyError, ValueError, TypeError):
            pass
    result['lastUpdated'] = stamp
    result['priceCheck'] = dict(evidence, checkedAt=stamp)
    return result


def update(catalog, client, now):
    result = copy.deepcopy(catalog)
    success = changed = failed = consecutive = 0
    started = time.monotonic()
    for i, product in enumerate(result['products']):
        if time.monotonic() - started > 600:
            raise RuntimeError('Limite de 10 minutos atingido; catálogo preservado')
        try:
            new = observe(product, client, now)
        except AuthError:
            raise
        except (RuntimeError, ValueError, TypeError) as exc:
            failed += 1
            consecutive += 1
            print(f'{product["id"]}: preservado — {exc}')
            if consecutive >= 5:
                raise RuntimeError('Cinco falhas consecutivas; verifique acesso à API. Catálogo preservado') from None
            continue
        success += 1
        consecutive = 0
        changed += new != product
        result['products'][i] = new
        if success % 50 == 0:
            print(f'{success} consultas confirmadas; {failed} falhas isoladas')
        time.sleep(0.1)
    print(f'Resumo: {success} confirmados; {changed} atualizados; {failed} preservados por falha')
    if not success:
        raise RuntimeError('Nenhum preço confirmado; catálogo preservado')
    return result, changed


def main():
    client = Client()
    current = catalogo.load(ROOT)
    updated, changed = update(current, client, datetime.now(timezone.utc))
    if not changed:
        print('Nenhuma mudança real no catálogo')
        return
    # Render and validate the whole catalog before any file is replaced.
    files = catalogo.render(updated, ROOT)
    files[catalogo.SOURCE.as_posix()] = catalogo.dumps(updated, pretty=True) + '\n'
    catalogo.write_files(files, ROOT)


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, ValueError) as exc:
        print(f'ERRO: {exc}', file=sys.stderr)
        raise SystemExit(1)
