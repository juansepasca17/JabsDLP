"""aria2: motor de descarga alternativo (opcional).

yt-dlp sigue analizando la página; aria2 solo baja los enlaces que yt-dlp obtiene, con varias conexiones.
aria2 no publica sumas SHA-256, así que la del zip oficial 1.37.0 está fijada aquí (comprobada también con el
manifiesto de Scoop).
"""
import hashlib
import os
import shutil
import sys
import threading
import urllib.request
import zipfile

from .ajustes import carpeta_local

VERSION = '1.37.0'
URL = f'https://github.com/aria2/aria2/releases/download/release-{VERSION}/aria2-{VERSION}-win-64bit-build1.zip'
SHA256 = '67d015301eef0b612191212d564c5bb0a14b5b9c4796b76454276a4d28d9b288'

descarga = {'estado': 'inactivo', 'progreso': 0.0, 'error': None}


def _carpeta_app():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def ruta(ajustes):
    candidatos = [(ajustes.get('aria2_ruta') or '').strip('"'),
                  os.path.join(_carpeta_app(), 'aria2c.exe'),
                  shutil.which('aria2c') or '',
                  os.path.join(carpeta_local(), 'aria2', 'aria2c.exe')]
    return next((c for c in candidatos if c and os.path.isfile(c)), None)


def carpeta_segura(ajustes):
    """Carpeta que solo contiene aria2c.exe, para ponerla en el PATH sin colar otros ejecutables de esa carpeta."""
    origen = ruta(ajustes)
    if not origen:
        return None
    propia = os.path.join(carpeta_local(), 'aria2')
    if os.path.normcase(os.path.dirname(origen)) == os.path.normcase(propia):
        return propia
    if shutil.which('aria2c') and os.path.normcase(shutil.which('aria2c')) == os.path.normcase(origen):
        return None  # ya está en el PATH del sistema
    try:
        os.makedirs(propia, exist_ok=True)
        destino = os.path.join(propia, 'aria2c.exe')
        if not os.path.isfile(destino) or os.path.getsize(destino) != os.path.getsize(origen):
            shutil.copyfile(origen, destino)
        return propia
    except OSError:
        return None


def descargar():
    if descarga['estado'] == 'descargando':
        return dict(descarga)
    descarga.update(estado='descargando', progreso=0.0, error=None)
    threading.Thread(target=_descargar, daemon=True).start()
    return dict(descarga)


def _descargar():
    destino = os.path.join(carpeta_local(), 'aria2')
    zip_tmp = os.path.join(carpeta_local(), 'aria2-descarga.zip')
    try:
        sha = hashlib.sha256()
        peticion = urllib.request.Request(URL, headers={'User-Agent': 'JabsDLP'})
        with urllib.request.urlopen(peticion, timeout=60) as resp, open(zip_tmp, 'wb') as f:
            total = int(resp.headers.get('Content-Length') or 0)
            hecho = 0
            while bloque := resp.read(1 << 16):
                f.write(bloque)
                sha.update(bloque)
                hecho += len(bloque)
                if total:
                    descarga['progreso'] = hecho / total * 0.95
        if sha.hexdigest() != SHA256:
            raise RuntimeError('La suma SHA-256 de aria2 no coincide; se descartó por seguridad.')
        os.makedirs(destino, exist_ok=True)
        with zipfile.ZipFile(zip_tmp) as z:
            miembro = next((m for m in z.namelist() if m.endswith('/aria2c.exe')), None)
            if not miembro:
                raise RuntimeError('El zip no contiene aria2c.exe')
            with z.open(miembro) as origen, open(os.path.join(destino, 'aria2c.exe'), 'wb') as salida:
                shutil.copyfileobj(origen, salida)
        descarga.update(estado='listo', progreso=1.0, error=None)
    except Exception as e:  # noqa: BLE001 - se muestra en Ajustes
        descarga.update(estado='error', progreso=0.0, error=str(e))
    finally:
        if os.path.exists(zip_tmp):
            try:
                os.unlink(zip_tmp)
            except OSError:
                pass


def instalado_por_la_app():
    return os.path.isdir(os.path.join(carpeta_local(), 'aria2'))


def desinstalar():
    """Borra la copia de aria2 de JabsDLP (%LOCALAPPDATA%\\JabsDLP\\aria2). No toca un aria2 instalado aparte."""
    carpeta = os.path.join(carpeta_local(), 'aria2')
    if os.path.isdir(carpeta):
        shutil.rmtree(carpeta)
    descarga.update(estado='inactivo', progreso=0.0, error=None)


VERSION_YTDLP_SEGURA = (2026, 6, 9)   # corrige CVE-2026-50574 (yt-dlp + aria2c con manifiestos DASH)


def ytdlp_seguro_para_aria2():
    """Por si alguna vez se cargara un yt-dlp antiguo: con versiones vulnerables no se usa aria2."""
    import yt_dlp
    from .actualizador import tupla
    return tupla(yt_dlp.version.__version__)[:3] >= VERSION_YTDLP_SEGURA


def argumentos(limite_bytes=0):
    """Argumentos para aria2c: 8 conexiones por archivo, sin preasignar disco, sin BitTorrent y con su límite."""
    args = ['-x', '8', '-s', '8', '-k', '1M', '--file-allocation=none', '--summary-interval=0',
            '--follow-torrent=false', '--follow-metalink=false', '--enable-dht=false', '--bt-enable-lpd=false']
    if limite_bytes > 0:
        args.append(f'--max-overall-download-limit={int(limite_bytes)}')
    return args


def argumentos_torrent(carpeta, limite_bytes=0, subida_kb=20):
    """Torrents: sin seed al terminar (--seed-time=0), subida limitada y sin leer configuraciones externas."""
    args = ['--no-conf', '--seed-time=0', '--seed-ratio=0.0', f'--max-overall-upload-limit={int(subida_kb)}K',
            '--file-allocation=none', '--summary-interval=1', '--console-log-level=warn', '--download-result=hide',
            '--follow-torrent=mem', '--bt-save-metadata=false', '--bt-enable-lpd=false', '--enable-peer-exchange=true',
            '--allow-overwrite=false', '--auto-file-renaming=true', '--enable-rpc=false', f'--dir={carpeta}']
    if limite_bytes > 0:
        args.append(f'--max-overall-download-limit={int(limite_bytes)}')
    return args
