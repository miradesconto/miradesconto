#!/usr/bin/env python3
"""Run the same official API checks as production without changing site data."""
from api_intelligence import main

if __name__ == '__main__':
    try:
        main(report_only=True)
    except (ValueError, RuntimeError, OSError):
        print('Diagnóstico oficial não concluído; consulte a configuração e a conexão.')
        raise SystemExit(1)
