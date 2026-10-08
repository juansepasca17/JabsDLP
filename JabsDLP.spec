# -*- mode: python ; coding: utf-8 -*-
# Compila un único JabsDLP.exe sin consola. Uso: .\build.ps1  (o: python -m PyInstaller --clean JabsDLP.spec)
# yt-dlp (incluidos los scripts de yt-dlp-ejs) y pywebview traen sus propios hooks de PyInstaller.
from PyInstaller.utils.hooks import collect_submodules, copy_metadata

# Metadatos de yt-dlp: el actualizador lee así la versión incluida sin importarla.
datas = [('ui', 'ui'), ('assets/icono.ico', 'assets')] + copy_metadata('yt-dlp') + copy_metadata('yt-dlp-ejs')

# Biblioteca estándar que una versión futura de yt-dlp (descargada por el actualizador) podría usar.
estandar = []
for paquete in ('email', 'html', 'http', 'xml', 'urllib', 'json', 'asyncio', 'concurrent', 'encodings',
                'importlib', 'sqlite3', 'zoneinfo', 'ctypes', 'multiprocessing', 'logging', 'collections'):
    estandar += collect_submodules(paquete)
estandar += ['hmac', 'secrets', 'uuid', 'zipfile', 'tarfile', 'lzma', 'bz2', 'gzip', 'netrc', 'getpass', 'shlex',
             'optparse', 'argparse', 'statistics', 'fractions', 'decimal', 'graphlib', 'dataclasses', 'contextvars',
             'selectors', 'ssl', 'mimetypes', 'difflib', 'textwrap', 'unicodedata', 'pprint', 'calendar', 'csv',
             'ipaddress', 'locale', 'pathlib', 'platform', 'queue', 'string', 'tempfile', 'traceback', 'heapq',
             'bisect', 'array', 'codecs', 'io', 'base64', 'binascii', 'struct', 'random', 'hashlib', 'functools']

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=estandar,
    hookspath=[],
    runtime_hooks=[],
    excludes=['tkinter', 'numpy', 'PIL', 'pytest', 'IPython', 'webview.platforms.qt', 'webview.platforms.gtk',
              'webview.platforms.cocoa', 'webview.platforms.android', 'webview.platforms.cef'],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='JabsDLP',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    icon='assets/icono.ico',
    version='version_info.txt',
)
