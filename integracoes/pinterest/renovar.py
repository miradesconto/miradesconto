"""Renova credenciais em GitHub Actions Secrets; não salva tokens no repositório."""
import os
import subprocess
from oauth_core import token_request, mask_for_actions


def save_with_gh(name, value):
    if name not in ('PINTEREST_ACCESS_TOKEN', 'PINTEREST_REFRESH_TOKEN'):
        raise ValueError('Nome de secret inválido.')
    proc = subprocess.run(
        ['gh', 'secret', 'set', name, '--repo', 'miradesconto/miradesconto'],
        input=value, text=True, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, check=False
    )
    if proc.returncode:
        raise RuntimeError('Falha ao atualizar os GitHub Secrets; revise GH_SECRETS_TOKEN.')


def main():
    keys = ('PINTEREST_APP_SECRET', 'PINTEREST_REFRESH_TOKEN', 'GH_TOKEN')
    missing = [key for key in keys if not os.getenv(key)]
    if missing:
        print('Renovação pendente: faltam ' + ', '.join(missing))
        return
    if os.getenv('GITHUB_REPOSITORY') != 'miradesconto/miradesconto':
        raise RuntimeError('Repositório diferente do esperado.')
    # Pré-verificação antes de solicitar rotação de refresh token.
    auth = subprocess.run(['gh', 'secret', 'list', '--repo', 'miradesconto/miradesconto'],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    if auth.returncode:
        raise RuntimeError('GH_TOKEN não possui acesso suficiente ao repositório.')
    tokens = token_request(os.environ['PINTEREST_APP_SECRET'], {
        'grant_type': 'refresh_token',
        'refresh_token': os.environ['PINTEREST_REFRESH_TOKEN']
    })
    mask_for_actions(tokens['access_token'])
    mask_for_actions(tokens['refresh_token'])
    save_with_gh('PINTEREST_REFRESH_TOKEN', tokens['refresh_token'])
    save_with_gh('PINTEREST_ACCESS_TOKEN', tokens['access_token'])
    print('OK: Pinterest OAuth renovado; novos tokens salvos apenas como GitHub Secrets.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError) as exc:
        print('ERRO:', str(exc))
        raise SystemExit(1)
