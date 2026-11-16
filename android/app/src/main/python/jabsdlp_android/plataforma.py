"""Lo que en Android funciona distinto que en Windows. Cada función llama a Kotlin (com.jabsdlp.app.Plataforma)."""
import os
import re
import shutil
import threading
import time

from jabsdlp.utilidades import es_medio

_nativo = None
_datos = None
DIAS_PAPELERA = 30


def configurar(nativo, datos):
    global _nativo, _datos
    _datos = datos
    if nativo is None:
        try:
            from java import jclass
            nativo = jclass('com.jabsdlp.app.Plataforma')
        except ImportError:   # fuera de Android (pruebas): sin efectos
            nativo = None
    _nativo = nativo


def _llamar(nombre, *args, defecto=None):
    if _nativo is None:
        return defecto
    try:
        resultado = getattr(_nativo, nombre)(*args)
    except Exception:  # noqa: BLE001 - un fallo de la parte nativa no debe tumbar la descarga
        return defecto
    return defecto if resultado is None else resultado


# ---------- abrir ----------
def abrir(ruta, seleccionar=False):
    """Abre un archivo multimedia con la app del sistema, o la carpeta en el gestor de archivos."""
    if not ruta or not os.path.exists(ruta):
        return False
    if os.path.isfile(ruta) and not es_medio(ruta):
        seleccionar = True   # como en el PC: nunca se abre directamente lo que no sea video o audio
    return bool(_llamar('abrir', str(ruta), bool(seleccionar), defecto=False))


# ---------- notificaciones ----------
def notificar(titulo, mensaje, archivo=None, carpeta=None, icono=None, textos=None):
    if archivo:
        escanear(archivo)
    _llamar('notificar', str(titulo or ''), str(mensaje or ''), str(archivo) if archivo else None)


def escanear(ruta):
    """Avisa al sistema de un archivo nuevo para que salga en la Galería y en Música."""
    if ruta and os.path.isfile(ruta):
        _llamar('escanear', str(ruta))


# ---------- portapapeles ----------
def leer_portapapeles():
    return str(_llamar('leerPortapapeles', defecto='') or '')


def copiar_portapapeles(texto):
    return bool(_llamar('copiarPortapapeles', str(texto or ''), defecto=False))


# ---------- ventana ----------
def tema_barra(hwnd, claro):
    _llamar('colorBarras', bool(claro))
    return True


# ---------- miniaturas de la Biblioteca ----------
_miniatura_pc = None


def miniatura(ruta, ffmpeg=None):
    """Como biblioteca.miniatura del PC, pero el fotograma lo saca Android (MediaMetadataRetriever): los videos de
    YouTube suelen venir en AV1 y el ffmpeg incluido no lo decodifica. Si Android no puede, se prueba con ffmpeg."""
    import base64
    import hashlib

    from jabsdlp import biblioteca
    from jabsdlp.ajustes import carpeta_local
    if biblioteca.tipo_archivo(ruta) != 'video' or not os.path.isfile(ruta):
        return None
    st = os.stat(ruta)
    clave = hashlib.sha1(f'{os.path.normcase(ruta)}|{st.st_mtime}|{st.st_size}'.encode('utf-8')).hexdigest()
    carpeta = os.path.join(carpeta_local(), 'miniaturas')
    os.makedirs(carpeta, exist_ok=True)
    cache = os.path.join(carpeta, clave + '.jpg')
    if not (os.path.isfile(cache) and os.path.getsize(cache) > 0):
        _llamar('miniatura', str(ruta), str(cache), defecto=False)
    if os.path.isfile(cache) and os.path.getsize(cache) > 0:
        with open(cache, 'rb') as f:
            return 'data:image/jpeg;base64,' + base64.b64encode(f.read()).decode('ascii')
    return _miniatura_pc(ruta, ffmpeg) if _miniatura_pc else None


# ---------- papelera ----------
def carpeta_papelera():
    ruta = os.path.join(_datos or os.environ.get('APPDATA', '.'), 'papelera')
    os.makedirs(ruta, exist_ok=True)
    return ruta


def papelera(ruta):
    """Android no tiene una papelera común para cualquier archivo: se mueve a la papelera de JabsDLP
    (memoria privada de la app) y se borra sola a los 30 días."""
    if not os.path.isfile(ruta):
        return False
    destino_dir = carpeta_papelera()
    nombre = os.path.basename(ruta)
    destino = os.path.join(destino_dir, f'{int(time.time())}-{nombre}')
    try:
        shutil.move(ruta, destino)
    except OSError:
        return False
    _llamar('escanear', str(ruta))   # que la Galería deje de mostrarlo
    threading.Thread(target=vaciar_papelera_antigua, daemon=True).start()
    return True


def vaciar_papelera_antigua():
    limite = time.time() - DIAS_PAPELERA * 86400
    try:
        for e in os.scandir(carpeta_papelera()):
            if e.is_file() and e.stat().st_mtime < limite:
                os.unlink(e.path)
    except OSError:
        pass


# ---------- diálogos ----------
def _tipos_mime(file_types):
    """('Video y audio (*.mp4;*.mkv)', 'Todos (*.*)') -> 'video/*,audio/*' o '*/*'."""
    extensiones = set()
    for filtro in file_types or ():
        extensiones.update(e.lower() for e in re.findall(r'\*\.(\w+)', str(filtro)))
    if extensiones & {'mp4', 'mkv', 'webm', 'mp3', 'm4a'}:
        return 'video/*,audio/*'
    return '*/*'


def _ruta_libre(carpeta, nombre):
    base, ext = os.path.splitext(nombre)
    ruta, n = os.path.join(carpeta, nombre), 2
    while os.path.exists(ruta):
        ruta = os.path.join(carpeta, f'{base} ({n}){ext}')
        n += 1
    return ruta


def adaptar_api(Api):
    """Sustituye en la clase Api del PC los métodos que dependen de la ventana de Windows."""

    def _dialogo(self, tipo, **kwargs):
        if tipo == 'SAVE':
            # Exportar: se guarda en la carpeta de descargas (Exportado) y se avisa de dónde quedó
            carpeta = os.path.join(self._ajustes.carpeta(), 'Exportado')
            os.makedirs(carpeta, exist_ok=True)
            ruta = _ruta_libre(carpeta, os.path.basename(kwargs.get('save_filename') or 'exportado'))
            _llamar('aviso', f'Guardado en {ruta}')
            return ruta
        mimes = _tipos_mime(kwargs.get('file_types'))
        resultado = _llamar('dialogo', tipo, mimes, defecto=None)
        return str(resultado) if resultado else None

    def reiniciar(self):
        resumen = self._gestor.resumen()
        if resumen['activos'] or resumen['en_cola']:
            return {'ok': False, 'error': 'Hay descargas en curso: espera a que terminen o cancélalas antes de reiniciar.'}
        self.cerrar()
        threading.Timer(0.3, lambda: _llamar('reiniciar')).start()
        return {'ok': True}

    def alternar_pantalla_completa(self):
        _llamar('pantallaCompleta', -1)
        return True

    def aplicar_tema_ventana(self, claro):
        return tema_barra(None, claro)

    def configurar_captura(self):
        return None   # en Android los enlaces llegan con "Compartir → JabsDLP"

    def _sin_aria2(self):
        return ('En Android todavía no se pueden descargar torrents: aria2, el programa que los descarga, '
                'no está disponible para celular. Descárgalo desde la versión de PC.')

    ver_pc = Api.ver

    def ver(self, origen, referer=None):
        from jabsdlp.utilidades import es_torrent
        if es_torrent((origen or '').strip()):
            try:
                import libtorrent  # noqa: F401
            except ImportError:
                return {'ok': False, 'error': 'En Android todavía no se pueden ver torrents: libtorrent no está '
                                              'disponible para celular. Puedes verlos en la versión de PC.'}
        return ver_pc(self, origen, referer)

    Api._sin_aria2 = _sin_aria2
    Api.ver = ver
    Api._dialogo = _dialogo
    Api.reiniciar = reiniciar
    Api.alternar_pantalla_completa = alternar_pantalla_completa
    Api.aplicar_tema_ventana = aplicar_tema_ventana
    Api.configurar_captura = configurar_captura
    Api.plataforma = lambda self: 'android'
