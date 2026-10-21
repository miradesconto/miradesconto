"""Valida a conexão Pinterest sem exigir user_accounts:read nem publicar Pins."""
import os
from api import pinterest_request


def check_collection(token, path, label):
    try:
        response = pinterest_request(token, path)
    except RuntimeError as exc:
        raise RuntimeError(f'Falha ao consultar {label}: {exc}') from None
    if not isinstance(response, dict) or not isinstance(response.get('items'), list):
        raise RuntimeError(f'Resposta de {label} inesperada.')


def main():
    access = os.getenv('PINTEREST_ACCESS_TOKEN', '').strip()
    check_collection(access, '/boards?page_size=1', 'pastas')
    check_collection(access, '/pins?page_size=1', 'Pins')
    print('OK: conexão Pinterest autenticada; pastas e Pins consultados. Nenhum Pin foi criado.')


if __name__ == '__main__':
    try:
        main()
    except RuntimeError as exc:
        print('ERRO:', str(exc))
        raise SystemExit(1)
