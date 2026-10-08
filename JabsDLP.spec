# -*- mode: python ; coding: utf-8 -*-
# Compila un único JabsDLP.exe sin consola. Uso: .\build.ps1  (o: python -m PyInstaller --clean JabsDLP.spec)
# yt-dlp (incluidos los scripts de yt-dlp-ejs) y pywebview traen sus propios hooks de PyInstaller.

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('ui', 'ui'), ('assets/icono.ico', 'assets')],
    hiddenimports=[],
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
