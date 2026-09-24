"""Troca um código OAuth de uso único por tokens guardados em GitHub Secrets."""
import os
import sys

from hourly_prices import ApiError, AuthError, gh, request

REDIRECT_URI = 'https://miradesconto.github.io/miradesconto/'


def main():
    required = ('CLIENT_ID', 'CLIENT_SECRET', 'ML_AUTH_CODE', 'GH_SECRETS_TOKEN')
    missing = [name for name in required if not os.getenv(name, '').strip()]
    if missing:
        raise AuthError('Secrets ausentes: ' + ', '.join(missing))
    repo = os.getenv('GITHUB_REPOSITORY')
    if repo != 'miradesconto/miradesconto':
        raise AuthError('Execute somente no repositório MiraDesconto')
    # Verifique a permissão antes de consumir o código de autorização único.
    gh(['secret', 'list', '--repo', repo, '--json', 'name'])
    try:
        result = request('/oauth/token', form={
            'grant_type': 'authorization_code',
            'client_id': os.environ['CLIENT_ID'],
            'client_secret': os.environ['CLIENT_SECRET'],
            'code': os.environ['ML_AUTH_CODE'].strip(),
            'redirect_uri': REDIRECT_URI,
        })
    except ApiError as exc:
        raise AuthError(
            f'Troca OAuth recusada pelo Mercado Livre (HTTP {exc.status}). '
            'O código pode ter vencido ou ter sido usado; confira também ID, chave e URI'
        ) from None
    except (RuntimeError, ValueError):
        raise AuthError('Troca OAuth falhou por rede ou resposta inválida; gere um novo código') from None
    access, refresh = result.get('access_token'), result.get('refresh_token')
    if not isinstance(access, str) or not access or not isinstance(refresh, str) or not refresh:
        raise AuthError('OAuth retornou tokens incompletos; gere um novo código')
    for value in (access, refresh):
        print('::add-mask::' + value.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A'), flush=True)
    try:
        gh(['secret', 'set', 'REFRESH_TOKEN', '--repo', repo], refresh)
        gh(['secret', 'set', 'ACCESS_TOKEN', '--repo', repo], access)
    except AuthError:
        raise AuthError('Tokens emitidos, mas não salvos. Gere um novo código após corrigir o acesso aos Secrets') from None
    gh(['secret', 'delete', 'ML_AUTH_CODE', '--repo', repo])
    print('Autorização concluída; ACCESS_TOKEN e REFRESH_TOKEN salvos. Código de uso único removido.')


if __name__ == '__main__':
    try:
        main()
    except (AuthError, RuntimeError, ValueError) as exc:
        print('ERRO: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
