import ctypes
import os
import re
import shutil
import subprocess
import sys

PATRON_URL = re.compile(r'https?://[^\s<>"\']+', re.IGNORECASE)

SIN_VENTANA = 0x08000000 if os.name == 'nt' else 0  # CREATE_NO_WINDOW


def extraer_urls(texto):
    vistas = set()
    urls = []
    for url in PATRON_URL.findall(texto or ''):
        url = url.rstrip('.,;)')
        if url not in vistas:
            vistas.add(url)
            urls.append(url)
    return urls


def leer_urls_txt(ruta):
    """Versión no interactiva de cargar_enlaces_desde_txt: una URL por línea."""
    if not ruta or os.path.isdir(ruta):
        raise ValueError('La ruta indicada es un directorio. Debes indicar un archivo .txt.')
    if not os.path.isfile(ruta):
        raise FileNotFoundError(f'No existe el archivo: {ruta}')
    with open(ruta, 'r', encoding='utf-8', errors='replace') as f:
        urls = extraer_urls(f.read())
    if not urls:
        raise ValueError('El archivo no contiene URLs válidas.')
    return urls


EXT_PELIGROSAS = ('exe', 'msi', 'bat', 'cmd', 'com', 'scr', 'pif', 'ps1', 'vbs', 'js', 'jse', 'wsf', 'hta', 'lnk',
                  'jar', 'reg', 'dll', 'cpl', 'msc', 'apk', 'appx', 'msix', 'iso', 'img', 'vhd', 'zip', 'rar', '7z')
EXT_MEDIOS = ('mp4', 'mkv', 'webm', 'mov', 'm4v', 'avi', 'flv', 'ts', 'mp3', 'm4a', 'opus', 'ogg', 'oga', 'flac', 'wav',
              'aac', 'wma', 'wmv', 'mka', '3gp', 'jpg', 'jpeg', 'png', 'webp', 'gif', 'srt', 'vtt', 'ass')


def es_torrent(texto):
    texto = (texto or '').strip()
    return texto.lower().startswith('magnet:?') or bool(re.match(r'^\S+\.torrent$', texto, re.I))


def nombre_torrent(texto):
    m = re.search(r'[?&]dn=([^&]+)', texto or '')
    if m:
        from urllib.parse import unquote_plus
        return unquote_plus(m.group(1))[:200]
    return os.path.basename(texto.split('?')[0]) if texto.lower().endswith('.torrent') else 'Torrent'


def extension_peligrosa(ruta_o_url):
    ext = os.path.splitext((ruta_o_url or '').split('?')[0].split('#')[0])[1].lower().lstrip('.')
    return ext in EXT_PELIGROSAS


def es_medio(ruta):
    return os.path.splitext(ruta or '')[1].lower().lstrip('.') in EXT_MEDIOS


def es_url_playlist(url):
    url = (url or '').lower()
    return 'list=' in url or '/playlist' in url or '/sets/' in url or '/album/' in url


def runtimes_js():
    """Runtimes de JavaScript que yt-dlp puede usar para resolver los retos de YouTube."""
    encontrados = {}
    for nombre in ('deno', 'node', 'bun'):
        ruta = shutil.which(nombre)
        if ruta:
            encontrados[nombre] = {'path': ruta}
    return encontrados


# (texto que aparece en el error de yt-dlp, código para traducir en la UI, mensaje en español, ¿es temporal?)
# Los temporales se reintentan solos; los definitivos (privado, no disponible...) no.
ERRORES = [
    ('HTTP Error 410', 'http410', 'No se puede descargar: error 410. La página no se descargó desde el servidor. '
                                  'Probablemente lo bloqueó por no coincidir el hash del video.', True),
    ('Sign in to confirm', 'bot', 'YouTube pide iniciar sesión para confirmar que no eres un bot. Configura cookies en Ajustes.', False),
    ('not a bot', 'bot', 'YouTube pide iniciar sesión para confirmar que no eres un bot. Configura cookies en Ajustes.', False),
    ('confirm your age', 'edad', 'Video con restricción de edad: configura cookies de una cuenta en Ajustes.', False),
    ('age-restricted', 'edad', 'Video con restricción de edad: configura cookies de una cuenta en Ajustes.', False),
    ('Private video', 'privado', 'El video es privado.', False),
    ('members-only', 'miembros', 'Video solo para miembros: necesitas cookies de una cuenta con acceso.', False),
    ('Video unavailable', 'no_disponible', 'El video no está disponible.', False),
    ('is unavailable', 'no_disponible', 'El video no está disponible.', False),
    ('playlist does not exist', 'playlist_no_existe', 'La playlist no existe o es privada.', False),
    ('is not available', 'no_disponible', 'El video no está disponible.', False),
    ('Unsupported URL', 'no_soportada', 'Esta URL no es compatible.', False),
    ('Requested format is not available', 'formato', 'El formato elegido ya no está disponible. Prueba con Auto.', False),
    ('ffmpeg is not installed', 'ffmpeg', 'Falta ffmpeg. Descárgalo desde Ajustes → Herramientas.', False),
    ('ffprobe and ffmpeg not found', 'ffmpeg', 'Falta ffmpeg. Descárgalo desde Ajustes → Herramientas.', False),
    ('Could not copy', 'cookies_copiar', 'No se pudieron leer las cookies del navegador (ciérralo o usa un archivo cookies.txt).', False),
    ('Failed to decrypt', 'cookies_descifrar', 'No se pudieron descifrar las cookies del navegador. Usa Firefox o un archivo cookies.txt.', False),
    ('HTTP Error 403', 'http403', 'El servidor rechazó la descarga (403). Prueba con cookies o actualiza la app.', True),
    ('HTTP Error 404', 'http404', 'No se encontró (404): el enlace no existe o ya caducó.', False),
    ('HTTP Error 429', 'http429', 'Demasiadas peticiones (429). Espera un poco o usa cookies.', True),
    ('HTTP Error 5', 'http5xx', 'El servidor tuvo un error temporal (5xx).', True),
    ('timed out', 'red', 'La conexión tardó demasiado en responder.', True),
    ('Connection reset', 'red', 'Se cortó la conexión con el servidor.', True),
    ('Connection aborted', 'red', 'Se cortó la conexión con el servidor.', True),
    ('Remote end closed', 'red', 'Se cortó la conexión con el servidor.', True),
    ('getaddrinfo failed', 'red', 'Sin conexión a internet (no se pudo resolver el servidor).', True),
    ('urlopen error', 'red', 'Error de red al conectar con el servidor.', True),
    ('IncompleteRead', 'red', 'La descarga se interrumpió a mitad.', True),
    ('fragment', 'fragmento', 'Falló la descarga de un fragmento del video.', True),
    ('Did not get any data blocks', 'fragmento', 'El servidor dejó de enviar datos.', True),
    ('aria2c exited with code', 'aria2', 'aria2 no pudo completar la descarga.', True),
]


def _limpiar_mensaje(mensaje):
    texto = re.sub(r'\x1b\[[0-9;]*m', '', str(mensaje or '')).strip()
    texto = re.sub(r'^ERROR:\s*', '', texto)
    return re.sub(r'^\[[\w:]+\]\s*[\w-]+:\s*', '', texto)


def clasificar_error(mensaje):
    """(código, mensaje en español, ¿temporal?) para un error de yt-dlp."""
    texto = _limpiar_mensaje(mensaje)
    for clave, codigo, amigable, temporal in ERRORES:
        if clave.lower() in texto.lower():
            return codigo, amigable, temporal
    return None, texto[:300] or 'Error desconocido', False


def error_amigable(mensaje):
    return clasificar_error(mensaje)[1]


def leer_portapapeles():
    if os.name != 'nt':
        return ''
    CF_UNICODETEXT = 13
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    user32.GetClipboardData.restype = ctypes.c_void_p
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    if not user32.OpenClipboard(None):
        return ''
    try:
        handle = user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return ''
        puntero = kernel32.GlobalLock(handle)
        try:
            return ctypes.wstring_at(puntero) if puntero else ''
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()


def copiar_portapapeles(texto):
    if os.name != 'nt':
        return False
    user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
    kernel32.GlobalAlloc.restype = ctypes.c_void_p
    kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalFree.argtypes = [ctypes.c_void_p]
    user32.SetClipboardData.restype = ctypes.c_void_p
    user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
    datos = (str(texto) + '\0').encode('utf-16-le')
    if not user32.OpenClipboard(None):
        return False
    try:
        user32.EmptyClipboard()
        handle = kernel32.GlobalAlloc(0x0002, len(datos))   # GMEM_MOVEABLE
        if not handle:
            return False
        puntero = kernel32.GlobalLock(handle)
        ctypes.memmove(puntero, datos, len(datos))
        kernel32.GlobalUnlock(handle)
        if not user32.SetClipboardData(13, handle):   # CF_UNICODETEXT; si va bien, Windows es el dueño
            kernel32.GlobalFree(handle)
            return False
        return True
    finally:
        user32.CloseClipboard()


def abrir_en_explorador(ruta, seleccionar=False):
    if not ruta or not os.path.exists(ruta):
        return False
    # Nunca se ejecuta un archivo descargado que no sea multimedia (p. ej. un .exe de un torrent):
    # en su lugar se muestra en su carpeta.
    if not seleccionar and os.path.isfile(ruta) and not es_medio(ruta):
        seleccionar = True
    if os.name == 'nt':
        if seleccionar:
            subprocess.Popen(['explorer', '/select,', os.path.normpath(ruta)], creationflags=SIN_VENTANA)
        else:
            os.startfile(ruta)
    else:
        subprocess.Popen(['open' if sys.platform == 'darwin' else 'xdg-open', ruta])
    return True


class Cancelado(Exception):
    """El usuario canceló la descarga."""


# ---------- enlaces directos de manifiesto (.m3u8 / .mpd) ----------
# Sufijos de dos niveles más habituales: el dominio "registrable" de cdn.algo.com.co es algo.com.co
SUFIJOS_DOBLES = {
    'com.co', 'org.co', 'edu.co', 'gov.co', 'net.co', 'com.mx', 'org.mx', 'edu.mx', 'gob.mx', 'com.ar', 'org.ar',
    'gob.ar', 'com.br', 'org.br', 'gov.br', 'com.pe', 'org.pe', 'gob.pe', 'com.ec', 'com.uy', 'com.ve', 'com.bo',
    'com.py', 'com.gt', 'com.do', 'cl.co', 'co.uk', 'org.uk', 'ac.uk', 'gov.uk', 'com.au', 'net.au', 'org.au',
    'co.jp', 'co.kr', 'co.in', 'co.nz', 'co.za', 'com.es', 'com.tr', 'com.cn', 'com.hk', 'com.tw', 'com.sg',
}
# Parámetros de la query que suelen ser tokens o firmas (se ocultan en el log y al copiar)
PARAMETROS_TOKEN = ('cp', 'pid', 'sid', 'uid', 'aid', 'token', 'tok', 'key', 'signature', 'sig', 'policy', 'hdnts',
                    'hdnea', 'hmac', 'auth', 'expires', 'key-pair-id', 'x-amz-signature', 'x-amz-credential',
                    'x-amz-security-token', 'access_token', 'jwt', 'st', 'e', 'hash')


def es_manifiesto(url):
    """'m3u8' o 'mpd' si la ruta (sin la query) es un manifiesto HLS/DASH; si no, None."""
    ruta = (url or '').strip().split('#', 1)[0].split('?', 1)[0].lower()
    if not ruta.startswith(('http://', 'https://')):
        return None
    for ext in ('m3u8', 'mpd'):
        if ruta.endswith('.' + ext):
            return ext
    return None


def referer_desde(url):
    """Página de origen deducida del dominio del manifiesto: mediastream.platzi.com -> https://platzi.com/."""
    from urllib.parse import urlsplit
    host = (urlsplit((url or '').strip()).hostname or '').lower().rstrip('.')
    if not host:
        return None
    if re.fullmatch(r'[\d.]+|\[?[0-9a-f:]+\]?', host):
        return f'https://{host}/'   # IP: no hay subdominio que quitar
    partes = host.split('.')
    n = 3 if len(partes) >= 3 and '.'.join(partes[-2:]) in SUFIJOS_DOBLES else 2
    return f"https://{'.'.join(partes[-n:])}/"


def nombre_manifiesto(url):
    """Nombre por defecto del archivo: el del manifiesto sin extensión (index-v1-a1), o 'video'."""
    from urllib.parse import unquote
    base = os.path.basename(unquote((url or '').split('#', 1)[0].split('?', 1)[0]))
    base = re.sub(r'\.(m3u8|mpd)$', '', base, flags=re.I)
    base = re.sub(r'[<>:"/\|?*\x00-\x1f]', '_', base).strip(' .')
    return base[:120] or 'video'


def _es_token(nombre):
    nombre = nombre.lower()
    return nombre in PARAMETROS_TOKEN or nombre.startswith('x-amz-')


def tiene_tokens(url):
    from urllib.parse import parse_qsl, urlsplit
    return any(_es_token(k) for k, _ in parse_qsl(urlsplit(url or '').query, keep_blank_values=True))


PATRON_PARAMETRO = re.compile(r'([?&;])([A-Za-z0-9_.\-]+)=([^&\s"\'<>#]*)')


def ocultar_tokens(texto):
    """Sustituye los valores de parámetros tipo token (cP, pid, sid, token, signature…) por ***."""
    if not texto:
        return texto
    return PATRON_PARAMETRO.sub(lambda m: f'{m.group(1)}{m.group(2)}=***' if _es_token(m.group(2)) and m.group(3) else m.group(0),
                                str(texto))
