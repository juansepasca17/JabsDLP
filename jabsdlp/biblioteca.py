"""Biblioteca: ver lo descargado sin abrir el Explorador (listar, miniaturas y enviar a la Papelera).

Solo se listan rutas dentro de las carpetas registradas (la de descargas y las que añadas): un '..' o un enlace
simbólico que salga de ellas se rechaza.
"""
import base64
import ctypes
import hashlib
import os
import subprocess
import threading
from ctypes import wintypes

from .ajustes import carpeta_local
from .utilidades import EXT_MEDIOS, SIN_VENTANA

MAX_ENTRADAS = 3000
EXT_VIDEO = ('mp4', 'mkv', 'webm', 'mov', 'm4v', 'avi', 'flv', 'ts', 'wmv', '3gp')
EXT_AUDIO = ('mp3', 'm4a', 'opus', 'ogg', 'oga', 'flac', 'wav', 'aac', 'wma', 'mka')
_semaforo = threading.Semaphore(2)   # como mucho 2 ffmpeg generando miniaturas a la vez


class RutaNoPermitida(ValueError):
    pass


def tipo_archivo(nombre):
    ext = os.path.splitext(nombre)[1].lower().lstrip('.')
    if ext in EXT_VIDEO:
        return 'video'
    if ext in EXT_AUDIO:
        return 'audio'
    return 'otro' if ext in EXT_MEDIOS else None


def dentro_de(ruta, raices):
    """True si `ruta` (resuelta) está dentro de alguna de las carpetas raíz."""
    real = os.path.normcase(os.path.realpath(ruta))
    for raiz in raices:
        base = os.path.normcase(os.path.realpath(raiz))
        if real == base or real.startswith(base.rstrip('\\/') + os.sep):
            return True
    return False


def _archivo(e, tipo, carpeta=''):
    st = e.stat()
    return {'nombre': e.name, 'ruta': e.path, 'tamano': st.st_size, 'fecha': st.st_mtime, 'tipo': tipo, 'carpeta': carpeta}


def _recorrer(destino):
    """Todos los archivos multimedia de destino y sus subcarpetas (sin las ocultas), como máximo MAX_ENTRADAS."""
    archivos, pendientes = [], [(destino, '')]
    while pendientes:
        carpeta, relativa = pendientes.pop(0)
        try:
            entradas = sorted(os.scandir(carpeta), key=lambda e: e.name.lower())
        except OSError:
            continue
        for e in entradas:
            if len(archivos) >= MAX_ENTRADAS:
                return archivos, True
            try:
                if e.is_dir(follow_symlinks=False):
                    if not e.name.startswith('.'):
                        pendientes.append((e.path, os.path.join(relativa, e.name) if relativa else e.name))
                    continue
                tipo = tipo_archivo(e.name)
                if tipo and not e.name.endswith(('.part', '.ytdl', '.temp')):
                    archivos.append(_archivo(e, tipo, relativa))
            except OSError:
                continue
    return archivos, False


def listar(raiz, sub='', raices=None, recursivo=False):
    """Carpetas y archivos multimedia de raiz/sub. Devuelve {'ruta', 'carpetas', 'archivos', 'recortado'}.
    Con recursivo, también los de todas las subcarpetas (cada archivo dice en qué subcarpeta está)."""
    raices = raices or [raiz]
    destino = os.path.normpath(os.path.join(raiz, sub or ''))
    if not dentro_de(destino, [raiz]) or not dentro_de(destino, raices):
        raise RutaNoPermitida('Esa carpeta está fuera de la Biblioteca.')
    if not os.path.isdir(destino):
        raise RutaNoPermitida('La carpeta ya no existe.')
    carpetas, archivos, recortado = [], [], False
    if recursivo:
        archivos, recortado = _recorrer(destino)
        archivos.sort(key=lambda a: a['fecha'], reverse=True)
        return {'ruta': destino, 'sub': os.path.relpath(destino, raiz) if destino != os.path.normpath(raiz) else '',
                'carpetas': [], 'archivos': archivos, 'recortado': recortado, 'recursivo': True}
    try:
        entradas = list(os.scandir(destino))
    except OSError as e:
        raise RutaNoPermitida(f'No se pudo leer la carpeta: {e.strerror or e}') from None
    for e in entradas:
        if len(carpetas) + len(archivos) >= MAX_ENTRADAS:
            recortado = True
            break
        try:
            if e.is_dir(follow_symlinks=False):
                if not e.name.startswith('.'):
                    carpetas.append({'nombre': e.name})
                continue
            tipo = tipo_archivo(e.name)
            if not tipo or e.name.endswith(('.part', '.ytdl', '.temp')):
                continue
            archivos.append(_archivo(e, tipo))
        except OSError:
            continue
    carpetas.sort(key=lambda c: c['nombre'].lower())
    archivos.sort(key=lambda a: a['fecha'], reverse=True)
    return {'ruta': destino, 'sub': os.path.relpath(destino, raiz) if destino != os.path.normpath(raiz) else '',
            'carpetas': carpetas, 'archivos': archivos, 'recortado': recortado}


def miniatura(ruta, ffmpeg):
    """data:image/jpeg;base64,… de un fotograma (cacheado), o None si no se puede."""
    if not ffmpeg or tipo_archivo(ruta) != 'video' or not os.path.isfile(ruta):
        return None
    st = os.stat(ruta)
    clave = hashlib.sha1(f'{os.path.normcase(ruta)}|{st.st_mtime}|{st.st_size}'.encode('utf-8')).hexdigest()
    carpeta = os.path.join(carpeta_local(), 'miniaturas')
    os.makedirs(carpeta, exist_ok=True)
    cache = os.path.join(carpeta, clave + '.jpg')
    if not os.path.isfile(cache):
        with _semaforo:
            for segundo in ('8', '1', '0'):
                try:
                    subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-nostdin', '-y', '-ss', segundo,
                                    '-i', ruta, '-frames:v', '1', '-vf', 'scale=320:-2', '-q:v', '6', cache],
                                   capture_output=True, timeout=20, creationflags=SIN_VENTANA)
                except (OSError, subprocess.SubprocessError):
                    return None
                if os.path.isfile(cache) and os.path.getsize(cache) > 0:
                    break
    if not os.path.isfile(cache) or os.path.getsize(cache) == 0:
        return None
    with open(cache, 'rb') as f:
        return 'data:image/jpeg;base64,' + base64.b64encode(f.read()).decode('ascii')


class _SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [('hwnd', wintypes.HWND), ('wFunc', wintypes.UINT), ('pFrom', wintypes.LPCWSTR),
                ('pTo', wintypes.LPCWSTR), ('fFlags', ctypes.c_ushort), ('fAnyOperationsAborted', wintypes.BOOL),
                ('hNameMappings', ctypes.c_void_p), ('lpszProgressTitle', wintypes.LPCWSTR)]


def papelera(ruta):
    """Envía un archivo a la Papelera de reciclaje (se puede recuperar). True si se movió."""
    if os.name != 'nt' or not os.path.isfile(ruta):
        return False
    FO_DELETE, FOF_SILENT, FOF_NOCONFIRMATION, FOF_ALLOWUNDO, FOF_NOERRORUI = 3, 0x4, 0x10, 0x40, 0x400
    op = _SHFILEOPSTRUCTW(None, FO_DELETE, os.path.abspath(ruta) + '\0', None,
                          FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI, False, None, None)
    resultado = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    return resultado == 0 and not op.fAnyOperationsAborted and not os.path.exists(ruta)
