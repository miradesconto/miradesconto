#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "index.html"

OLD_BLOCK = '''<section class="editorial"><div class="editorial-head"><div><h2>Antes de comprar</h2></div><a href="blog/">Explorar pautas →</a></div><div class="editorial-grid"><a class="editorial-card" href="blog/#reviews"><small>REVIEWS</small><h3>Vale a pena comprar?</h3><p>Perguntas sobre produtos reais para futuras análises.</p></a><a class="editorial-card" href="blog/#comparativos"><small>COMPARATIVOS</small><h3>Qual produto faz mais sentido?</h3><p>Produtos do catálogo para futuras comparações, sem vencedor antecipado.</p></a><a class="editorial-card" href="blog/#guias"><small>GUIAS</small><h3>Como escolher sem errar</h3><p>Pautas para investigar critérios de escolha antes da compra.</p></a></div></section>'''

NEW_BLOCK = '''<section class="editorial"><div class="editorial-head"><div><h2>Antes de comprar</h2></div><a href="blog/">Ver todos os conteúdos →</a></div><div class="editorial-grid">{% assign published_home = site.artigos | where: "status", "publicado" | sort: "data" | reverse %}{% for entry in published_home limit: 3 %}<a class="editorial-card" href="{{ entry.url | relative_url }}"><small>{% case entry.categoria %}{% when 'reviews' %}REVIEW{% when 'comparativos' %}COMPARATIVO{% else %}GUIA{% endcase %}</small><h3>{{ entry.title | escape }}</h3><p>{{ entry.resumo | escape }}</p></a>{% endfor %}</div></section>'''


def main() -> int:
    text = INDEX.read_text(encoding="utf-8")
    changed = text

    if not changed.startswith("---\n"):
        changed = "---\nlayout: null\n---\n" + changed

    if OLD_BLOCK in changed:
        changed = changed.replace(OLD_BLOCK, NEW_BLOCK)
    elif "published_home" not in changed:
        raise RuntimeError("Bloco editorial da home mudou e não pôde ser atualizado automaticamente.")

    if changed != text:
        INDEX.write_text(changed, encoding="utf-8")
        print("Home preparada para exibir automaticamente os artigos publicados mais recentes.")
    else:
        print("Home editorial já está automatizada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
