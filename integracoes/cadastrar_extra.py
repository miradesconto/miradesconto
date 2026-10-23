#!/usr/bin/env python3
"""Valida novos links individuais de Amazon, Shopee ou Mercado Livre, sem publicar Pins."""
import argparse
import json
from pathlib import Path
from campanha import ROOT, validate_extras, generate
import catalogo

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    incoming=catalogo.read_json(args.input)
    existing=catalogo.read_json(ROOT/'_data/afiliados_extras.json')
    products=catalogo.public_data(catalogo.read_json(ROOT/'dados/catalogo.json'))['products']
    proposed=validate_extras(existing+incoming,products)
    print(str(len(incoming))+' produtos validados; preços serão consultados na loja.')
    if args.apply:
        target=ROOT/'_data/afiliados_extras.json'
        target.write_text(catalogo.dumps(proposed,pretty=True)+'\n')
        generate()
        print('Cadastro e destinos dos produtos gerados. Revise e publique pelo GitHub.')
    else:
        print('Prévia concluída. Para gravar, execute com --apply.')
