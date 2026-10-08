import copy
import json
import os
import threading

from . import APP_NAME
from .cookies import NAVEGADORES
from .formatos import CRITERIOS, NIVELES_AUDIO, normalizar


def carpeta_datos():
    base = os.environ.get('APPDATA') or os.path.expanduser('~')
    ruta = os.path.join(base, APP_NAME)
    os.makedirs(ruta, exist_ok=True)
    return ruta


def carpeta_local():
    base = os.environ.get('LOCALAPPDATA') or carpeta_datos()
    ruta = os.path.join(base, APP_NAME)
    os.makedirs(ruta, exist_ok=True)
    return ruta


def carpeta_videos_por_defecto():
    return os.path.join(os.path.expanduser('~'), 'Videos', APP_NAME)


PREFS_POR_DEFECTO = {
    'tipo': 'video',            # video | audio
    'codec': 'auto',            # auto | h264 | h265 | av1 | vp9
    'resolucion': 'auto',       # auto | 2160 | 1440 | 1080 | 720 | 480 | 360
    'contenedor': 'auto',       # auto | mp4 | mkv | webm
    'audio': 'auto',            # auto (con audio) | no (sin audio) | custom (pista o calidad elegida)
    'audio_calidad': 'alta',    # alta | media | baja (audio personalizado en playlists)
    'criterio': 'equilibrado',  # equilibrado (menor tamaño sin perder calidad) | ahorro | calidad
    'formato_audio': 'auto',    # auto | mp3 | m4a | opus | flac
    'metadatos': True,
    'miniatura': True,
    'subtitulos': False,
}

AJUSTES_POR_DEFECTO = {
    'carpeta': '',                      # vacío = carpeta_videos_por_defecto()
    'subcarpeta_playlist': True,
    'plantilla': '%(title)s.%(ext)s',
    'cookies_modo': 'ninguna',          # ninguna | archivo | navegador
    'cookies_archivo': '',
    'cookies_navegador': 'firefox',
    'paralelo': True,
    'max_paralelo': 0,                  # 0 = sin límite
    'fragmentos': 4,
    'max_conversiones': 2,
    'gpu': 'auto',                      # auto | amf | nvenc | qsv | cpu
    'decodificar_gpu': True,
    'calidad': 26,                      # QP/CQ de la GPU; en CPU se usa calidad + 2 como CRF (26 -> 28, como tu script)
    'ffmpeg_ruta': '',
    'idiomas_subtitulos': 'es.*,en.*',
    'recomendacion': True,              # mostrar siempre una opción recomendada (Auto)
    'prefs': PREFS_POR_DEFECTO,
}


BOOLEANOS = ('subcarpeta_playlist', 'paralelo', 'decodificar_gpu', 'recomendacion')
ENTEROS = {'max_paralelo': (0, 999), 'fragmentos': (1, 32), 'max_conversiones': (1, 16), 'calidad': (10, 45)}
OPCIONES = {
    'cookies_modo': ('ninguna', 'archivo', 'navegador'),
    'cookies_navegador': NAVEGADORES,
    'gpu': ('auto', 'amf', 'nvenc', 'qsv', 'cpu'),
}
OPCIONES_PREFS = {
    'tipo': ('video', 'audio'),
    'codec': ('auto', 'h264', 'h265', 'av1', 'vp9'),
    'resolucion': ('auto', '2160', '1440', '1080', '720', '480', '360'),
    'contenedor': ('auto', 'mp4', 'mkv', 'webm'),
    'audio': ('auto', 'no', 'custom'),
    'audio_calidad': NIVELES_AUDIO,
    'criterio': CRITERIOS,
    'formato_audio': ('auto', 'mp3', 'm4a', 'opus', 'flac'),
}
NO_VALIDO = object()


def validar(clave, valor):
    """Devuelve el valor saneado o NO_VALIDO. Protege la ruta de ffmpeg (se ejecuta) y la plantilla."""
    if clave in BOOLEANOS:
        return bool(valor)
    if clave in ENTEROS:
        try:
            minimo, maximo = ENTEROS[clave]
            return max(minimo, min(maximo, int(valor)))
        except (TypeError, ValueError):
            return NO_VALIDO
    if clave in OPCIONES:
        return valor if valor in OPCIONES[clave] else NO_VALIDO
    if not isinstance(valor, str):
        return NO_VALIDO
    valor = valor.strip().strip('"')
    if clave == 'ffmpeg_ruta':
        if not valor:
            return ''
        es_exe = os.path.basename(valor).lower() == 'ffmpeg.exe' and os.path.isfile(valor)
        es_carpeta = os.path.isfile(os.path.join(valor, 'ffmpeg.exe'))
        return valor if es_exe or es_carpeta else NO_VALIDO
    if clave == 'plantilla':
        partes = valor.replace('\\', '/').split('/')
        absoluta = os.path.isabs(valor) or valor.startswith(('/', '\\')) or ':' in valor.split('%')[0]
        if not valor or absoluta or '..' in partes:
            return NO_VALIDO
        return valor
    if clave in ('carpeta', 'cookies_archivo', 'idiomas_subtitulos'):
        return valor
    return NO_VALIDO


def validar_prefs(prefs):
    limpias = {}
    for clave, valor in (prefs or {}).items():
        if clave in OPCIONES_PREFS:
            if str(valor) in OPCIONES_PREFS[clave]:
                limpias[clave] = str(valor)
            elif clave == 'audio' and isinstance(valor, bool):
                limpias[clave] = valor
        elif clave in ('metadatos', 'miniatura', 'subtitulos'):
            limpias[clave] = bool(valor)
    return limpias


class Ajustes:
    def __init__(self, ruta=None):
        self.ruta = ruta or os.path.join(carpeta_datos(), 'settings.json')
        self._lock = threading.RLock()
        self._datos = copy.deepcopy(AJUSTES_POR_DEFECTO)
        self._cargar()

    def _cargar(self):
        try:
            with open(self.ruta, 'r', encoding='utf-8') as f:
                guardados = json.load(f)
        except (OSError, ValueError):
            return
        if not isinstance(guardados, dict):
            return
        self._aplicar(guardados)

    @staticmethod
    def _prefs_validas(prefs):
        return {k: v for k, v in normalizar(prefs).items() if k in PREFS_POR_DEFECTO}

    def _guardar(self):
        temporal = self.ruta + '.tmp'
        with open(temporal, 'w', encoding='utf-8') as f:
            json.dump(self._datos, f, ensure_ascii=False, indent=2)
        os.replace(temporal, self.ruta)

    def todo(self):
        with self._lock:
            datos = copy.deepcopy(self._datos)
        datos['carpeta_efectiva'] = self.carpeta()
        return datos

    def get(self, clave):
        with self._lock:
            return copy.deepcopy(self._datos.get(clave, AJUSTES_POR_DEFECTO.get(clave)))

    def _aplicar(self, cambios):
        for clave, valor in (cambios or {}).items():
            if clave == 'prefs' and isinstance(valor, dict):
                self._datos['prefs'].update(validar_prefs(valor))
                self._datos['prefs'] = self._prefs_validas(self._datos['prefs'])
            elif clave in AJUSTES_POR_DEFECTO:
                limpio = validar(clave, valor)
                if limpio is not NO_VALIDO:
                    self._datos[clave] = limpio

    def actualizar(self, cambios):
        with self._lock:
            self._aplicar(cambios if isinstance(cambios, dict) else {})
            self._guardar()
        return self.todo()

    def carpeta(self):
        carpeta = self.get('carpeta') or carpeta_videos_por_defecto()
        return os.path.expandvars(os.path.expanduser(carpeta))
