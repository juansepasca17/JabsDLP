"""Analiza una URL (video o playlist) sin descargar: metadatos, miniatura y formatos."""
import re
import threading
import uuid
from collections import OrderedDict

import yt_dlp

from .cookies import borrar_temporal, opciones_cookies
from .formatos import clase
from .impersonacion import aplicar_impersonacion
from .utilidades import EXT_PELIGROSAS, es_url_playlist, extension_peligrosa, runtimes_js

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
