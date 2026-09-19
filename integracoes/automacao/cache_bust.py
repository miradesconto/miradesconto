#!/usr/bin/env python3
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "index.html"
ASSETS = ["carrossel.css", "catalogo.css", "produtos.js", "interface.js", "carrossel.js"]


def main() -> int:
    text = INDEX.read_text(encoding="utf-8")
    token = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    changed = text
    for asset in ASSETS:
        pattern = rf"{re.escape(asset)}(?:\?v=[^\"']+)?"
        changed = re.sub(pattern, f"{asset}?v={token}", changed)
    if changed != text:
        INDEX.write_text(changed, encoding="utf-8")
        print(f"Cache-bust atualizado: {token}")
    else:
        print("Nenhuma referência de asset encontrada para atualizar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
