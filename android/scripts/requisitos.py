"""Escribe android/requirements-android.txt con la última versión de yt-dlp y el yt-dlp-ejs que esa versión fija.

yt-dlp rechaza cualquier yt-dlp-ejs distinto del que fija su pyproject, así que se leen los metadatos de la
rueda de yt-dlp en vez de pedir "lo último" de los dos por separado. Lo usa el workflow antes de compilar.
Uso: python android/scripts/requisitos.py
"""
import email
import glob
import os
import re
import subprocess
import sys
import tempfile
import zipfile

ANDROID = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESTINO = os.path.join(ANDROID, 'requirements-android.txt')
FIJOS = ['certifi', 'mutagen', 'requests', 'urllib3']   # Python puro: funcionan en Chaquopy tal cual


def main():
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([sys.executable, '-m', 'pip', 'download', '--quiet', '--no-deps', '--only-binary', ':all:',
                        '-d', tmp, 'yt-dlp'], check=True)
        rueda = glob.glob(os.path.join(tmp, 'yt_dlp-*.whl'))[0]
        with zipfile.ZipFile(rueda) as z:
            nombre = next(n for n in z.namelist() if n.endswith('.dist-info/METADATA'))
            meta = email.message_from_bytes(z.read(nombre))
    version = meta['Version']
    ejs = None
    for req in meta.get_all('Requires-Dist') or []:
        m = re.match(r'yt-dlp-ejs\s*\(?\s*==\s*([\w.]+)', req)
        if m:
            ejs = m.group(1)
            break
    lineas = ['# Generado por android/scripts/requisitos.py (no editar a mano en el workflow)',
              f'yt-dlp=={version}', f'yt-dlp-ejs=={ejs}' if ejs else 'yt-dlp-ejs', *FIJOS]
    with open(DESTINO, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lineas) + '\n')
    print('\n'.join(lineas[1:]))


if __name__ == '__main__':
    main()
