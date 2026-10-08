import os
import sys

# En el .exe sin consola (PyInstaller --windowed) stdout/stderr son None y yt-dlp escribe en ellos
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w', encoding='utf-8')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w', encoding='utf-8')

import webview  # noqa: E402

from jabsdlp import APP_NAME  # noqa: E402
from jabsdlp.api import Api  # noqa: E402


def recurso(*partes):
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *partes)


def diagnostico(salida, url=None):
    """JabsDLP.exe --diagnostico informe.json [URL]: versiones, ffmpeg, GPU y (opcional) análisis de una URL."""
    import json
    import yt_dlp
    api = Api()
    informe = {'app': APP_NAME, 'ytdlp': yt_dlp.version.__version__, 'herramientas': api.detectar_gpu()}
    if url:
        r = api.analizar(url, 'auto', None)
        datos = r.get('datos') or {}
        informe['analisis'] = {'ok': r.get('ok'), 'error': r.get('error'), 'titulo': datos.get('titulo'),
                               'formatos': len(datos.get('opciones') or []),
                               'recomendado': (datos.get('recomendado') or {}).get('titulo')}
    with open(salida, 'w', encoding='utf-8') as f:
        json.dump(informe, f, ensure_ascii=False, indent=2)


def main():
    if '--diagnostico' in sys.argv:
        resto = sys.argv[sys.argv.index('--diagnostico') + 1:]
        diagnostico(resto[0] if resto else 'jabsdlp_diagnostico.json', resto[1] if len(resto) > 1 else None)
        return
    api = Api()
    ventana = webview.create_window(
        APP_NAME,
        url=recurso('ui', 'index.html'),
        js_api=api,
        width=1320,
        height=860,
        min_size=(1000, 660),
        background_color='#09090b',
    )
    api._ventana = ventana
    ventana.events.closing += lambda: api.cancelar_todo()
    icono = recurso('assets', 'icono.ico')
    webview.start(debug='--debug' in sys.argv, icon=icono if os.path.exists(icono) else None)


if __name__ == '__main__':
    main()
