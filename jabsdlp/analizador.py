"""Analiza una URL (video o playlist) sin descargar: metadatos, miniatura y formatos."""
import re
import threading
import time
import uuid
from collections import OrderedDict
from urllib.parse import urlsplit

import yt_dlp

from .cookies import borrar_temporal, opciones_cookies
from .formatos import clase
from .impersonacion import aplicar_impersonacion
from .utilidades import (EXT_PELIGROSAS, clasificar_error, es_manifiesto, es_url_playlist, extension_peligrosa,
                         nombre_manifiesto, ocultar_tokens, referer_desde, runtimes_js, tiene_tokens)

MAX_CACHE = 40


class Silencioso:
    def debug(self, msg):
        pass

    info = warning = debug

    def error(self, msg):
        pass


def _miniatura(info, ancho_max=None):
    miniaturas = [t for t in info.get('thumbnails') or [] if t.get('url')]
    if ancho_max and miniaturas:
        con_ancho = [t for t in miniaturas if t.get('width')]
        adecuadas = [t for t in con_ancho if t['width'] >= 300] or con_ancho
        if adecuadas:
            return min(adecuadas, key=lambda t: t['width'])['url']
    if info.get('thumbnail'):
        return info['thumbnail']
    return miniaturas[-1]['url'] if miniaturas else None


def nombre_sitio(info):
    clave = re.sub(r'(Tab|Playlist|Channel|User|Search|Clip)$', '', info.get('extractor_key') or info.get('extractor') or '')
    return {'youtube': 'YouTube', 'vimeo': 'Vimeo', 'twitch': 'Twitch', 'tiktok': 'TikTok'}.get(clave.lower(), clave or None)


def riesgos(url, info):
    """Avisos para fuentes de riesgo: sin cifrar, sitio no soportado (extractor genérico) o archivo ejecutable."""
    lista = []
    if (info.get('webpage_url') or url or '').lower().startswith('http://'):
        lista.append('http')
    if (info.get('extractor_key') or '') in ('Generic', 'HTML5MediaEmbed'):
        lista.append('generico')
    if extension_peligrosa(url) or (info.get('ext') or '').lower() in EXT_PELIGROSAS:
        lista.append('ejecutable')
    return lista


def idiomas_audio(formatos):
    """Idiomas de las pistas de audio (YouTube marca el original con language_preference alto)."""
    vistos = {}
    for f in formatos:
        if clase(f) != 'audio' or not f.get('language'):
            continue
        codigo = f['language']
        nota = (f.get('format_note') or '').lower()
        original = (f.get('language_preference') or 0) >= 10 or 'original' in nota
        if codigo not in vistos or original:
            nombre = re.sub(r',?\s*(low|medium|high|ultralow|DRC)\b.*$', '', f.get('format_note') or '', flags=re.I).strip(' ,')
            vistos[codigo] = {'codigo': codigo, 'nombre': nombre or codigo, 'original': original}
    return sorted(vistos.values(), key=lambda i: (not i['original'], i['codigo']))


def idiomas_subtitulos(info):
    manuales = [{'codigo': c, 'nombre': (v[0].get('name') if v else None) or c, 'auto': False}
                for c, v in (info.get('subtitles') or {}).items() if c != 'live_chat']
    automaticos = info.get('automatic_captions') or {}
    originales = [c for c in automaticos if c.endswith('-orig')]
    return {'manuales': manuales, 'hay_automaticos': bool(automaticos),
            'automaticos': sorted(c for c in automaticos if '-' not in c or c in originales)[:120]}


class Analizador:
    def __init__(self, ajustes):
        self._ajustes = ajustes
        self._cache = OrderedDict()
        self._lock = threading.Lock()

    def _opciones(self):
        opciones = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'logger': Silencioso(),
        }
        runtimes = runtimes_js()
        if runtimes:
            opciones['js_runtimes'] = runtimes
        aplicar_impersonacion(opciones, self._ajustes)
        return opciones

    def analizar(self, url, modo='auto'):
        playlist = modo == 'playlist' or (modo == 'auto' and es_url_playlist(url))
        opciones = self._opciones()
        opciones['noplaylist'] = not playlist
        if playlist:
            opciones['extract_flat'] = 'in_playlist'
        extra, temporal = opciones_cookies(self._ajustes)
        opciones.update(extra)
        try:
            with yt_dlp.YoutubeDL(opciones) as ydl:
                info = ydl.sanitize_info(ydl.extract_info(url, download=False))
        finally:
            borrar_temporal(temporal)

        if info.get('_type') in ('playlist', 'multi_video') or info.get('entries') is not None:
            return self._playlist(url, info)
        return self._video(url, info)

    def _guardar(self, datos):
        with self._lock:
            self._cache[datos['id']] = datos
            while len(self._cache) > MAX_CACHE:
                self._cache.popitem(last=False)

    def obtener(self, id_):
        with self._lock:
            return self._cache.get(id_)

    def _video(self, url, info):
        formatos = info.get('formats') or []
        videos = [f for f in formatos if clase(f) in ('video', 'combinado') and f.get('height')]
        mejor = max(videos, key=lambda f: (f.get('height') or 0, f.get('fps') or 0, f.get('tbr') or 0)) if videos else {}
        datos = {
            'tipo': 'video',
            'id': uuid.uuid4().hex[:12],
            'url': info.get('webpage_url') or url,
            'titulo': info.get('title') or url,
            'canal': info.get('channel') or info.get('uploader'),
            'duracion': info.get('duration'),
            'vistas': info.get('view_count'),
            'likes': info.get('like_count'),
            'fecha': info.get('upload_date'),
            'miniatura': _miniatura(info),
            'extractor': nombre_sitio(info),
            'resolucion': f"{mejor['width']}x{mejor['height']}" if mejor.get('width') else
                          (f"{mejor['height']}p" if mejor.get('height') else info.get('resolution')),
            'fps': mejor.get('fps') or info.get('fps'),
            'tbr': mejor.get('tbr') or info.get('tbr'),
            'en_vivo': bool(info.get('is_live')),
            'video_id': info.get('id'),
            'sitio_clave': info.get('extractor_key'),
            'idiomas_audio': idiomas_audio(formatos),
            'idiomas_subs': idiomas_subtitulos(info),
            'riesgos': riesgos(url, info),
        }
        self._guardar({**datos, '_info': {'formats': formatos, 'duration': info.get('duration')}})
        return datos

    def _playlist(self, url, info):
        entradas = []
        for i, e in enumerate(info.get('entries') or [], start=1):
            if not e:
                continue
            enlace = e.get('webpage_url') or e.get('url')
            if enlace and not enlace.startswith('http') and e.get('ie_key') == 'Youtube':
                enlace = f'https://www.youtube.com/watch?v={enlace}'
            if not enlace or not enlace.startswith('http'):
                continue
            entradas.append({
                'indice': e.get('playlist_index') or i,
                'url': enlace,
                'titulo': e.get('title') or enlace,
                'duracion': e.get('duration'),
                'miniatura': _miniatura(e, ancho_max=480),
                'canal': e.get('channel') or e.get('uploader'),
                'video_id': e.get('id'),
                'sitio_clave': e.get('ie_key') or info.get('extractor_key'),
            })
        if not entradas:
            raise ValueError('La playlist está vacía o no se pudieron leer sus videos.')
        datos = {
            'tipo': 'playlist',
            'id': uuid.uuid4().hex[:12],
            'url': info.get('webpage_url') or url,
            'titulo': info.get('title') or 'Playlist',
            'canal': info.get('channel') or info.get('uploader'),
            'cantidad': len(entradas),
            'miniatura': _miniatura(info) or entradas[0]['miniatura'],
            'extractor': nombre_sitio(info),
            'duracion': sum(e['duracion'] or 0 for e in entradas) or None,
            'entradas': entradas,
        }
        self._guardar(datos)
        return datos

    # ---------- enlaces directos de manifiesto (.m3u8 / .mpd) ----------
    def analizar_manifiesto(self, url, referer=None):
        """Comprobación previa sin descargar el video: ¿responde el manifiesto con este Referer?

        Usa las mismas opciones que la descarga (Referer, cookies, impersonation solo si está activada) y además
        lee el texto del manifiesto para contar fragmentos, sumar la duración y detectar cifrado.
        """
        ext = es_manifiesto(url)
        deducido = referer_desde(url)
        referer = ''.join(str(referer or '').split())[:500] or deducido   # cabecera HTTP: sin saltos de línea
        datos = {
            'tipo': 'manifiesto', 'id': uuid.uuid4().hex[:12], 'url': url, 'formato': ext,
            'host': urlsplit(url).hostname, 'referer': referer, 'referer_deducido': deducido,
            'nombre': nombre_manifiesto(url), 'tokens': tiene_tokens(url), 'riesgos': [],
            'prueba': {'ok': False, 'motivo': None, 'codigo': None, 'fragmentos': None, 'duracion': None,
                       'variantes': None, 'cifrado': None, 'resolucion': None},
        }
        if url.lower().startswith('http://'):
            datos['riesgos'].append('http')
        prueba = datos['prueba']
        opciones = self._opciones()
        opciones.update(noplaylist=True, socket_timeout=15, extractor_retries=0,
                        http_headers={'Referer': referer} if referer else {})
        extra, temporal = opciones_cookies(self._ajustes)
        opciones.update(extra)
        try:
            with yt_dlp.YoutubeDL(opciones) as ydl:
                try:
                    info = ydl.extract_info(url, download=False)
                except yt_dlp.utils.DownloadError as e:
                    if clasificar_error(e)[0] != 'red':
                        raise
                    time.sleep(1.5)   # un fallo de red/DNS pasajero no debe marcar el enlace como caído
                    info = ydl.extract_info(url, download=False)
                info = ydl.sanitize_info(info)
                formatos = info.get('formats') or []
                videos = [f for f in formatos if f.get('height')]
                if videos:
                    mejor = max(videos, key=lambda f: (f.get('height') or 0, f.get('tbr') or 0))
                    prueba['resolucion'] = f"{mejor['height']}p"
                prueba['duracion'] = info.get('duration')
                prueba['variantes'] = len(formatos) or None
                prueba['ok'] = True
                # Texto del manifiesto (o de la variante de más calidad si es un maestro HLS)
                try:
                    texto = self._leer(ydl, url, referer)
                    if ext == 'm3u8' and '#EXT-X-STREAM-INF' in texto and formatos:
                        variante = (videos and max(videos, key=lambda f: (f.get('height') or 0, f.get('tbr') or 0))
                                    or formatos[-1]).get('url')
                        if variante and variante != url:
                            texto = self._leer(ydl, variante, referer)
                    prueba.update(_resumen_manifiesto(texto, ext))
                    if not prueba['duracion'] and prueba.get('suma'):
                        prueba['duracion'] = prueba['suma']
                    prueba.pop('suma', None)
                except Exception:  # noqa: BLE001 - el análisis ya respondió; el recuento es un extra
                    pass
        except Exception as e:  # noqa: BLE001 - se muestra en la interfaz; se puede descargar igualmente
            codigo, texto, _ = clasificar_error(e)
            prueba['codigo'] = codigo
            prueba['motivo'] = {
                'http403': 'El servidor rechazó la petición (403): revisa la página de origen, vuelve a copiar el '
                           'enlace o activa la suplantación de navegador en Ajustes.',
                'http410': 'El enlace caducó (410): el token ya no es válido; vuelve a copiar el enlace.',
                'red': texto,
            }.get(codigo, texto)
            prueba['detalle'] = ocultar_tokens(str(e))[:2000]
        finally:
            borrar_temporal(temporal)
        self._guardar(datos)
        return datos

    @staticmethod
    def _leer(ydl, url, referer, limite=5 << 20):
        from yt_dlp.networking import Request
        with ydl.urlopen(Request(url, headers={'Referer': referer} if referer else {})) as resp:
            return resp.read(limite).decode('utf-8', 'replace')


def _resumen_manifiesto(texto, ext):
    """Fragmentos, duración sumada y cifrado (AES-128 de HLS o DRM) a partir del texto del manifiesto."""
    if ext == 'm3u8':
        duraciones = [float(m) for m in re.findall(r'#EXTINF:\s*([\d.]+)', texto)]
        metodos = re.findall(r'#EXT-X-(?:SESSION-)?KEY:[^\n]*METHOD=([\w-]+)', texto)
        cifrado = None
        if any(m.upper() != 'NONE' for m in metodos):
            drm = re.search(r'KEYFORMAT="(?!identity)[^"]+"', texto) or any(m.upper() == 'SAMPLE-AES' for m in metodos)
            cifrado = 'drm' if drm else 'aes'
        return {'fragmentos': len(duraciones) or None, 'suma': sum(duraciones) or None, 'cifrado': cifrado}
    repeticiones = [re.search(r'\br="(\d+)"', s) for s in re.findall(r'<S\b[^>]*>', texto)]
    fragmentos = len(re.findall(r'<SegmentURL\b', texto)) or \
        sum(int(r.group(1)) + 1 if r else 1 for r in repeticiones) or None
    # Duración ISO 8601 del MPD: mediaPresentationDuration="PT0H10M54.00S"
    m = re.search(r'mediaPresentationDuration="P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:([\d.]+)S)?"', texto)
    suma = None
    if m:
        d, h, mi, s = (float(x) if x else 0.0 for x in m.groups())
        suma = d * 86400 + h * 3600 + mi * 60 + s or None
    return {'fragmentos': fragmentos, 'suma': suma, 'cifrado': 'drm' if '<ContentProtection' in texto else None}
