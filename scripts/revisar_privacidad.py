"""Revisión de privacidad antes de publicar.

Busca datos personales y secretos en los archivos del proyecto y, si existe, dentro de dist/JabsDLP.exe
(incluido el código Python empaquetado). Los datos personales NO están escritos aquí: se obtienen de tu
usuario de Windows, tu carpeta personal y tu configuración de git. Puedes añadir más con --extra.

Uso:  python scripts/revisar_privacidad.py [--exe dist/JabsDLP.exe] [--extra "texto1" "texto2"]
Sale con código 1 si encuentra algo.
"""
import argparse
import os
import re
import subprocess
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXCLUIR = {'.venv', 'venv', 'build', 'dist', '__pycache__', '.pytest_cache', '.git', '.claude', '.vs', '.vscode'}
BINARIOS = {'.ico', '.png', '.jpg', '.jpeg', '.webp', '.exe', '.zip', '.pyc'}
SECRETOS = {
    'token de GitHub': r'gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}',
    'clave de Google': r'AIza[0-9A-Za-z_-]{30,}',
    'clave de API': r'\bsk-[A-Za-z0-9]{20,}',
    'token de Slack': r'xox[abpr]-[A-Za-z0-9-]{10,}',
    'clave privada': r'-----BEGIN [A-Z ]*PRIVATE KEY-----',
    'cookie de sesión': r'\t(SAPISID|SID|HSID|SSID|APISID|__Secure-[13]PSID[A-Z]*|LOGIN_INFO)\t[^\t\r\n]{8,}',
    'correo electrónico': r'[A-Za-z0-9._%+-]+@(gmail|hotmail|outlook|yahoo|icloud|live)\.[a-z.]{2,}',
}


def git(*args):
    try:
        return subprocess.run(['git', *args], capture_output=True, text=True, timeout=10).stdout.strip()
    except OSError:
        return ''


def terminos_personales(extra):
    terminos = set(extra or [])
    usuario = os.environ.get('USERNAME') or os.environ.get('USER')
    if usuario and len(usuario) >= 3:
        terminos.add(usuario)
    casa = os.path.expanduser('~')
    terminos.update({casa, casa.replace('\\', '/'), casa.replace('\\', '\\\\')})
    correo = git('config', '--get', 'user.email')
    if correo and 'noreply' not in correo and not correo.endswith('example.com'):
        terminos.add(correo)
    return sorted(t for t in terminos if t)


def buscar(texto, terminos):
    hallazgos = []
    bajo = texto.lower()
    for t in terminos:
        if t.lower() in bajo:
            hallazgos.append(f'dato personal «{t}»')
    for nombre, patron in SECRETOS.items():
        m = re.search(patron, texto)
        if m and not m.group(0).endswith('@users.noreply.github.com'):
            hallazgos.append(f'{nombre}: «{m.group(0)[:40]}»')
    return hallazgos


def archivos_proyecto():
    for base, carpetas, archivos in os.walk(RAIZ):
        carpetas[:] = [c for c in carpetas if c not in EXCLUIR]
        for nombre in archivos:
            if os.path.splitext(nombre)[1].lower() not in BINARIOS:
                yield os.path.join(base, nombre)


def nombres_en_codigo(codigo):
    yield codigo.co_filename
    for constante in codigo.co_consts:
        if isinstance(constante, types.CodeType):
            yield from nombres_en_codigo(constante)


def revisar_exe(ruta, terminos):
    from PyInstaller.archive.readers import CArchiveReader
    hallazgos = []
    with open(ruta, 'rb') as f:
        crudo = f.read()
    for t in terminos:
        for codificado in (t.encode('utf-8'), t.encode('utf-16-le')):
            if codificado.lower() in crudo.lower():
                hallazgos.append(f'{os.path.basename(ruta)}: dato personal «{t}» en el binario')
                break
    archivo = CArchiveReader(ruta)
    for nombre, entrada in archivo.toc.items():
        tipo = entrada[-1]
        if tipo == 'z':  # PYZ con los módulos Python
            pyz = archivo.open_embedded_archive(nombre)
            for modulo in pyz.toc:
                try:
                    codigo = pyz.extract(modulo)
                except Exception:  # noqa: BLE001 - paquetes de espacio de nombres, etc.
                    continue
                if isinstance(codigo, types.CodeType):
                    for archivo_fuente in set(nombres_en_codigo(codigo)):
                        for h in buscar(archivo_fuente, terminos):
                            hallazgos.append(f'{nombre}/{modulo}: {h}')
        else:
            try:
                datos = archivo.extract(nombre)
            except Exception:  # noqa: BLE001
                continue
            if isinstance(datos, (bytes, bytearray)) and tipo in ('s', 'm', 'x', 'o', 'u', 'd'):
                texto = datos.decode('utf-8', 'ignore')
                for h in buscar(texto, terminos):
                    hallazgos.append(f'{nombre}: {h}')
    return hallazgos


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--exe', default=os.path.join(RAIZ, 'dist', 'JabsDLP.exe'))
    parser.add_argument('--extra', nargs='*', default=[], help='Textos adicionales que no deben aparecer')
    args = parser.parse_args()
    terminos = terminos_personales(args.extra)
    print(f'Buscando {len(terminos)} datos personales y {len(SECRETOS)} tipos de secreto…')

    hallazgos = []
    revisados = 0
    for ruta in archivos_proyecto():
        revisados += 1
        try:
            with open(ruta, 'r', encoding='utf-8', errors='ignore') as f:
                texto = f.read()
        except OSError:
            continue
        for h in buscar(texto, terminos):
            hallazgos.append(f'{os.path.relpath(ruta, RAIZ)}: {h}')
    print(f'  Archivos del proyecto revisados: {revisados}')

    if os.path.isfile(args.exe):
        hallazgos += revisar_exe(args.exe, terminos)
        print(f'  Ejecutable revisado: {os.path.relpath(args.exe, RAIZ)}')
    else:
        print('  (No hay .exe compilado todavía; solo se revisó el código)')

    if hallazgos:
        print('\n❌ Se encontraron datos que no deberían publicarse:')
        for h in hallazgos:
            print('   -', h)
        sys.exit(1)
    print('\n✅ Sin datos personales ni secretos.')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
