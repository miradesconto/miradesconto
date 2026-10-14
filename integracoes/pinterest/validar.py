"""Teste de leitura, sem qualquer publicação."""
import os
from api import pinterest_request


def main():
    access = os.getenv('PINTEREST_ACCESS_TOKEN', '').strip()
    account = pinterest_request(access, '/user_account')
    boards = pinterest_request(access, '/boards?page_size=1')
    if not isinstance(account, dict) or not isinstance(boards, dict) or 'items' not in boards:
        raise RuntimeError('Respostas de usuário/pastas inesperadas.')
    print('OK: conexão Pinterest autenticada, usuário e pastas consultados. Nenhum Pin foi criado.')


if __name__ == '__main__':
    try:
        main()
    except RuntimeError as exc:
        print('ERRO:', str(exc))
        raise SystemExit(1)
