"""Comprueba que cada función pública de jabsdlp/api.py esté en android/funciones.txt o en android/solo_pc.txt.

Uso: python android/scripts/revisar_api.py   (sale con código 1 si falta alguna o sobra alguna)
"""
import ast
import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SOLO_ANDROID = {'plataforma'}   # las añade jabsdlp_android/plataforma.py


def publicas():
    with open(os.path.join(RAIZ, 'jabsdlp', 'api.py'), encoding='utf-8') as f:
        arbol = ast.parse(f.read())
    clase = next(n for n in arbol.body if isinstance(n, ast.ClassDef) and n.name == 'Api')
    return {n.name for n in clase.body if isinstance(n, ast.FunctionDef) and not n.name.startswith('_')}


def leer(nombre, con_valor=False):
    salida = {}
    with open(os.path.join(RAIZ, 'android', nombre), encoding='utf-8') as f:
        for n, linea in enumerate(f, 1):
            linea = linea.strip()
            if not linea or linea.startswith('#'):
                continue
            clave, _, valor = linea.partition('=')
            if con_valor and valor.strip():
                try:
                    json.loads(valor)
                except ValueError:
                    sys.exit(f'{nombre}:{n}: la respuesta de "{clave.strip()}" no es JSON válido')
            salida[clave.strip()] = valor.strip()
    return salida


def main():
    api = publicas()
    funciones, solo_pc = set(leer('funciones.txt')), set(leer('solo_pc.txt', con_valor=True))
    errores = []
    if faltan := sorted(api - funciones - solo_pc):
        errores.append('Funciones nuevas en api.py sin clasificar (añádelas a android/funciones.txt o android/solo_pc.txt): '
                       + ', '.join(faltan))
    if sobran := sorted((funciones | solo_pc) - api - SOLO_ANDROID):
        errores.append('Funciones que ya no existen en api.py (quítalas de las listas): ' + ', '.join(sobran))
    if dobles := sorted(funciones & solo_pc):
        errores.append('Funciones en las dos listas: ' + ', '.join(dobles))
    if errores:
        print('\n'.join(errores))
        sys.exit(1)
    print(f'OK: {len(funciones)} funciones en Android, {len(solo_pc)} solo de PC.')


if __name__ == '__main__':
    main()
