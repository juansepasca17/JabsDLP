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


ERRORES = [
    ('HTTP Error 410', 'No se puede descargar: error 410. La página no se descargó desde el servidor. '
                       'Probablemente lo bloqueó por no coincidir el hash del video.'),
    ('Sign in to confirm', 'YouTube pide iniciar sesión para confirmar que no eres un bot. Configura cookies en Ajustes.'),
    ('not a bot', 'YouTube pide iniciar sesión para confirmar que no eres un bot. Configura cookies en Ajustes.'),
    ('confirm your age', 'Video con restricción de edad: configura cookies de una cuenta en Ajustes.'),
    ('age-restricted', 'Video con restricción de edad: configura cookies de una cuenta en Ajustes.'),
    ('Private video', 'El video es privado.'),
    ('members-only', 'Video solo para miembros: necesitas cookies de una cuenta con acceso.'),
    ('Video unavailable', 'El video no está disponible.'),
    ('is unavailable', 'El video no está disponible.'),
    ('playlist does not exist', 'La playlist no existe o es privada.'),
    ('is not available', 'El video no está disponible.'),
    ('Unsupported URL', 'Esta URL no es compatible.'),
    ('Requested format is not available', 'El formato elegido ya no está disponible. Prueba con Auto.'),
    ('ffmpeg is not installed', 'Falta ffmpeg. Descárgalo desde Ajustes → Herramientas.'),
    ('ffprobe and ffmpeg not found', 'Falta ffmpeg. Descárgalo desde Ajustes → Herramientas.'),
    ('Could not copy', 'No se pudieron leer las cookies del navegador (ciérralo o usa un archivo cookies.txt).'),
    ('Failed to decrypt', 'No se pudieron descifrar las cookies del navegador. Usa Firefox o un archivo cookies.txt.'),
    ('HTTP Error 403', 'El servidor rechazó la descarga (403). Prueba con cookies o actualiza la app.'),
    ('HTTP Error 429', 'Demasiadas peticiones (429). Espera un poco o usa cookies.'),
]


def error_amigable(mensaje):
    texto = re.sub(r'\x1b\[[0-9;]*m', '', str(mensaje or '')).strip()
    texto = re.sub(r'^ERROR:\s*', '', texto)
    texto = re.sub(r'^\[[\w:]+\]\s*[\w-]+:\s*', '', texto)
    for clave, amigable in ERRORES:
        if clave.lower() in texto.lower():
            return amigable
    return texto[:300] or 'Error desconocido'


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


def abrir_en_explorador(ruta, seleccionar=False):
    if not ruta or not os.path.exists(ruta):
        return False
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
