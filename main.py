import os
import sys

# En el .exe sin consola (PyInstaller --windowed) stdout/stderr son None y yt-dlp escribe en ellos
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w', encoding='utf-8')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w', encoding='utf-8')

import webview  # noqa: E402

from jabsdlp import APP_NAME, actualizador  # noqa: E402
from jabsdlp import procesos  # noqa: E402

procesos.proteger()  # ffmpeg/aria2 mueren con la app aunque se cierre de golpe

# yt-dlp actualizado (si se descargó uno más nuevo que el incluido); si no importa bien, se usa el incluido
if actualizador.activar():
    try:
        import yt_dlp  # noqa: F401
        import yt_dlp.postprocessor  # noqa: F401
    except Exception as e:  # noqa: BLE001
        import traceback
        actualizador.desactivar(f'{type(e).__name__}: {e}')
        try:
            with open(os.path.join(actualizador.carpeta(), 'error-carga.txt'), 'w', encoding='utf-8') as f:
                traceback.print_exc(file=f)
        except OSError:
            pass

from jabsdlp.api import Api  # noqa: E402


def recurso(*partes):
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *partes)


def diagnostico(salida, url=None):
    """JabsDLP.exe --diagnostico informe.json [URL]: versiones, ffmpeg, GPU y (opcional) análisis de una URL."""
    import json
    import yt_dlp
    from jabsdlp.impersonacion import impersonation_disponible
    api = Api()
    disponible, motivo = impersonation_disponible()
    informe = {'app': APP_NAME, 'ytdlp': yt_dlp.version.__version__, 'ytdlp_modulo': yt_dlp.__file__,
               'impersonacion': {'disponible': disponible, 'motivo': motivo},
               'herramientas': api.detectar_gpu()}
    try:
        import libtorrent
        informe['libtorrent'] = libtorrent.__version__
    except Exception as e:  # noqa: BLE001
        informe['libtorrent'] = f'no disponible: {e}'
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
    # Una sola instancia: si ya está abierta (p. ej. oculta en la bandeja), se muestra esa y esta se cierra
    reinicio = os.environ.pop('JABSDLP_REINICIO', None) == '1'
    if not procesos.instancia_unica(esperar=15.0 if reinicio else 0.0):
        procesos.avisar_instancia_abierta()
        return
    api = Api()
    claro = api._ajustes.get('tema') == 'claro'
    ancho, alto = 1320, 860
    try:  # que quepa sobre la barra de tareas (pantallas de 1080p al 125 %, portátiles…)
        import ctypes
        from jabsdlp.captura import area_trabajo
        izq, arriba, der, abajo = area_trabajo()
        escala = ctypes.windll.user32.GetDpiForSystem() / 96.0
        ancho = max(1000, min(ancho, int((der - izq) / escala) - 40))
        alto = max(660, min(alto, int((abajo - arriba) / escala) - 40))
    except (AttributeError, OSError):
        pass
    ventana = webview.create_window(
        APP_NAME,
        url=recurso('ui', 'index.html'),
        js_api=api,
        width=ancho,
        height=alto,
        min_size=(1000, 660),
        background_color='#f4f4f7' if claro else '#09090b',   # sin fogonazo oscuro en el tema claro
        fullscreen=bool(api._ajustes.get('pantalla_completa')),
    )
    api._ventana = ventana

    # Burbuja para sugerir enlaces copiados (Ajustes → Captura rápida). Oculta hasta que haga falta.
    api._burbuja = webview.create_window(
        'JabsDLP · enlace', url=recurso('ui', 'burbuja.html'), js_api=api, width=440, height=112,
        frameless=True, on_top=True, hidden=True, focus=False, resizable=False,
        background_color='#f4f4f7' if claro else '#111115')

    def al_mostrar():
        # La barra de título sigue el tema de la app (pywebview la pone según el de Windows)
        from jabsdlp.ventana import tema_barra
        tema = api._ajustes.get('tema')
        if tema != 'sistema':
            tema_barra(api._hwnd(), tema == 'claro')
        api.configurar_captura()

    ventana.events.shown += al_mostrar
    # La X cierra la app: con "retomar" se guardan los pendientes para continuarlos al reabrir
    ventana.events.closing += lambda: api.cerrar()

    # Minimizar → se oculta en la bandeja y las descargas siguen (si está activado en Ajustes)
    bandeja = None

    def mostrar():
        if bandeja is not None:
            bandeja.ocultar()
        ventana.show()
        ventana.restore()

    procesos.escuchar_mostrar(mostrar)   # abrir JabsDLP otra vez muestra esta ventana

    png = recurso('assets', 'icono.png')
    if os.path.exists(png):
        from jabsdlp.bandeja import Bandeja

        bandeja = Bandeja(
            png, mostrar=mostrar,
            pausar=lambda pausar: api.pausar_cola(pausar),
            abrir_carpeta=lambda: api.abrir_carpeta(None),
            salir=ventana.destroy,
            estado=lambda: (api._gestor.resumen()['activos'], api._gestor.pausado),
            textos=api.textos,
        )

        def al_minimizar():
            if api._ajustes.get('bandeja_al_minimizar'):
                ventana.hide()
                bandeja.mostrar_icono()

        ventana.events.minimized += al_minimizar
        ventana.events.closed += bandeja.ocultar

    def al_cerrar():
        api._detener_captura()
        try:
            api._burbuja.destroy()   # sin esto la app seguiría viva con la burbuja oculta
        except Exception:  # noqa: BLE001
            pass

    ventana.events.closed += al_cerrar

    icono = recurso('assets', 'icono.ico')
    webview.start(debug='--debug' in sys.argv, icon=icono if os.path.exists(icono) else None)


if __name__ == '__main__':
    main()
