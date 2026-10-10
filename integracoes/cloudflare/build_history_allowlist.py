"""IDs atuais e anteriores conhecidos, sem preços ou históricos na lista."""
import json
import argparse
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--check', action='store_true')
args = parser.parse_args()
catalog = json.loads((ROOT / 'dados/catalogo.json').read_text(encoding='utf-8'))
archive = json.loads((ROOT / 'links-afiliados.json').read_text(encoding='utf-8'))
ids = {p['id'] for p in catalog['products']} | {p['id'] for p in archive}
target = Path(__file__).with_name('history-items.json')
if target.exists():
    ids.update(json.loads(target.read_text(encoding='utf-8')))
if not ids or any(not re.fullmatch(r'MLB\d{7,14}', key) for key in ids):
    raise ValueError('ID histórico inválido')
content = json.dumps(sorted(ids), indent=2)+'\n'
if args.check:
    if not target.exists() or target.read_text(encoding='utf-8') != content:
        raise ValueError('Regere build_history_allowlist.py antes do deploy')
else:
    target.write_text(content, encoding='utf-8')
print(f'Identidades conhecidas para histórico: {len(ids)}')
