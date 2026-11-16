"""Prepara el entorno de Android y adapta los módulos del PC antes de crear la Api.

El orden importa: los módulos de jabsdlp/ copian algunas funciones con `from .utilidades import x`
al importarse, así que las sustituciones se hacen ANTES de importar api.py, trabajo.py, etc.
"""
import os
import sys
import types

from . import plataforma

_preparado = False


def _enlazar_binarios(bin_dir, nativos):
    """ffmpeg, ffprobe y qjs viven en nativeLibraryDir (lo único ejecutable en Android) con nombre lib*.so.
    Se enlazan con su nombre normal en una carpeta del PATH: así el código del PC los encuentra con shutil.which."""
    os.makedirs(bin_dir, exist_ok=True)
    for nombre, so in (('ffmpeg', 'libffmpeg.so'), ('ffprobe', 'libffprobe.so'), ('qjs', 'libqjs.so'),
                       ('aria2c', 'libaria2c.so')):
        origen = os.path.join(nativos, so)
        destino = os.path.join(bin_dir, nombre)
        try:
            if os.path.islink(destino) or os.path.exists(destino):
                if os.path.realpath(destino) == os.path.realpath(origen):
                    continue
                os.unlink(destino)
            if os.path.isfile(origen):
                os.symlink(origen, destino)
        except OSError:
            pass


def _certificados():
    """Python en Android no trae la lista de autoridades del sistema: se usa la de certifi."""
    try:
        import certifi
        ruta = certifi.where()
        os.environ.setdefault('SSL_CERT_FILE', ruta)
        os.environ.setdefault('REQUESTS_CA_BUNDLE', ruta)
    except Exception:  # noqa: BLE001
        pass


def _modulo_falso(nombre, **funciones):
    mod = types.ModuleType(nombre)
    mod.__dict__.update(funciones)
    sys.modules[nombre] = mod
    return mod


def preparar(datos, cache, descargas, nativos, nativo=None):
    """datos: filesDir · cache: cacheDir · descargas: carpeta por defecto (Download/JabsDLP)
    nativos: nativeLibraryDir · nativo: objeto Kotlin com.jabsdlp.app.Plataforma (o un sustituto en pruebas)."""
    global _preparado
    if _preparado:
        return
    plataforma.configurar(nativo, datos)

    # Carpetas: el PC usa %APPDATA% y %LOCALAPPDATA%; aquí apuntan a la memoria privada de la app
    os.environ['APPDATA'] = datos
    os.environ['LOCALAPPDATA'] = os.path.join(datos, 'local')
    os.environ['HOME'] = datos
    os.environ['TMPDIR'] = cache
    os.makedirs(os.environ['LOCALAPPDATA'], exist_ok=True)
    import tempfile
    tempfile.tempdir = cache

    bin_dir = os.path.join(datos, 'bin')
    _enlazar_binarios(bin_dir, nativos)
    os.environ['PATH'] = bin_dir + os.pathsep + os.environ.get('PATH', '/system/bin')
    _certificados()

    # Módulos que en el PC usan APIs de Windows al importarse: se reemplazan por los de Android
    _modulo_falso('jabsdlp.notificar', mostrar=plataforma.notificar, APP_ID='JabsDLP')
    _modulo_falso('jabsdlp.ventana', hwnd_por_titulo=lambda *a: None, tema_barra=plataforma.tema_barra,
                  mostrar_sin_foco=lambda *a: None, ocultar=lambda *a: None, escala=lambda *a: 1.0)

    from jabsdlp import ajustes, utilidades
    ajustes.carpeta_videos_por_defecto = lambda: descargas
    utilidades.abrir_en_explorador = plataforma.abrir
    utilidades.leer_portapapeles = plataforma.leer_portapapeles
    utilidades.copiar_portapapeles = plataforma.copiar_portapapeles
    runtimes_pc = utilidades.runtimes_js

    def runtimes_js():
        encontrados = runtimes_pc()
        qjs = os.path.join(bin_dir, 'qjs')
        if not encontrados and os.path.isfile(qjs):
            encontrados['quickjs'] = {'path': qjs}   # QuickJS resuelve los retos de YouTube (no hay deno/node)
        return encontrados
    utilidades.runtimes_js = runtimes_js

    # yt-dlp descargado por el actualizador (si hay uno más nuevo que el incluido), igual que main.py del PC
    from jabsdlp import actualizador
    if actualizador.activar():
        try:
            import yt_dlp  # noqa: F401
            import yt_dlp.postprocessor  # noqa: F401
        except Exception as e:  # noqa: BLE001
            actualizador.desactivar(f'{type(e).__name__}: {e}')

    from jabsdlp import biblioteca
    biblioteca.papelera = plataforma.papelera
    plataforma._miniatura_pc = biblioteca.miniatura
    biblioteca.miniatura = plataforma.miniatura

    # Ver torrents: libtorrent4j (Kotlin) en lugar del libtorrent de Python, que no existe para Android
    from jabsdlp import ver_torrent
    from .torrents import TorrentsAndroid
    ver_torrent.Torrents = TorrentsAndroid

    from jabsdlp.api import Api
    plataforma.adaptar_api(Api)
    _preparado = True
