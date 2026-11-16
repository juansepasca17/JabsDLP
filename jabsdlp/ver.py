"""Pestaña Ver: decide cómo reproducir un enlace o un archivo dentro de la app (sin descargarlo).

Orden de preferencia para un enlace (yt-dlp extrae la información):
  1. HLS (manifiesto .m3u8, p. ej. el de YouTube): hls.js en la interfaz, todo a través del proxy local.
  2. Un archivo progresivo con video y audio que el navegador sabe reproducir: directo (con Range).
  3. Video y audio separados (DASH, .mpd…): ffmpeg los une al vuelo (remux); saltar reinicia desde ese segundo.
Para un archivo local: directo si el navegador lo admite; si no, remux (o transcodificación si el códec no se puede).
"""
import json
import os
import subprocess
import time

from .ajustes import carpeta_datos
from .utilidades import SIN_VENTANA, es_manifiesto, ocultar_tokens, referer_desde

VIDEO_COMPATIBLE = ('avc1', 'h264', 'vp8', 'vp9', 'vp09', 'av01', 'av1')
AUDIO_COMPATIBLE = ('mp4a', 'aac', 'opus', 'vorbis', 'mp3', 'flac')
EXT_DIRECTAS = ('.mp4', '.m4v', '.webm', '.mov', '.mp3', '.m4a', '.ogg', '.oga', '.opus', '.wav', '.flac', '.aac')
IDIOMAS_PREFERIDOS = ('es', 'en')
MAX_VISTOS = 30


class NoReproducible(ValueError):
    pass


def _compatible(codec, lista):
    codec = (codec or '').lower()
    return bool(codec) and codec != 'none' and codec.startswith(lista)


# ---------- archivos locales ----------
def sondear(ruta, ffprobe, espera=None):
    """(códec de video o None, códec de audio o None, duración, pistas de subtítulos [(índice, idioma, título)],
    pistas de audio [(índice, idioma, título)])."""
    if not ffprobe:
        return None, None, None, [], []
    try:
        r = subprocess.run([ffprobe, '-v', 'error', '-show_entries', 'stream=codec_type,codec_name:stream_tags=language,title'
                            ':format=duration', '-of', 'json', ruta], capture_output=True,
                           timeout=espera or 20, creationflags=SIN_VENTANA)
        datos = json.loads(r.stdout or b'{}')
    except (OSError, subprocess.SubprocessError, ValueError):
        return None, None, None, [], []
    video = next((s['codec_name'] for s in datos.get('streams', []) if s.get('codec_type') == 'video'
                  and s.get('codec_name') not in ('mjpeg', 'png')), None)
    audio = next((s['codec_name'] for s in datos.get('streams', []) if s.get('codec_type') == 'audio'), None)
    subs = [(n, (s.get('tags') or {}).get('language'), (s.get('tags') or {}).get('title'))
            for n, s in enumerate([s for s in datos.get('streams', []) if s.get('codec_type') == 'subtitle'])]
    audios = [(n, (s.get('tags') or {}).get('language'), (s.get('tags') or {}).get('title'))
              for n, s in enumerate([s for s in datos.get('streams', []) if s.get('codec_type') == 'audio'])]
    try:
        duracion = float((datos.get('format') or {}).get('duration'))
    except (TypeError, ValueError):
        duracion = None
    return video, audio, duracion, subs, audios


def _nombres_audio(pistas):
    return [{'idioma': (idioma or '').lower(), 'nombre': titulo or idioma or f'Pista {n + 1}', 'original': False}
            for n, idioma, titulo in pistas]


def resolver_local(ruta, proxy, ffprobe):
    if not os.path.isfile(ruta):
        raise NoReproducible('No se encontró el archivo (¿lo moviste o borraste?).')
    video, audio, duracion, pistas, audios = sondear(ruta, ffprobe)
    ext = os.path.splitext(ruta)[1].lower()
    titulo = os.path.splitext(os.path.basename(ruta))[0]
    base = {'titulo': titulo, 'duracion': duracion, 'canal': None, 'miniatura': None, 'origen': ruta,
            'solo_audio': not video, 'subtitulos': []}
    # con varias pistas de audio se une al vuelo: el navegador no deja elegir el audio de un archivo directo
    if (len(audios) < 2 and ext in EXT_DIRECTAS and (not video or _compatible(video, VIDEO_COMPATIBLE))
            and (not audio or _compatible(audio, AUDIO_COMPATIBLE))):
        base.update(modo='directo', src=proxy.local(ruta))
    else:
        transcodificar = bool(video) and not _compatible(video, VIDEO_COMPATIBLE)
        base.update(modo='remux', src=proxy.remux([(ruta, None)], transcodificar=transcodificar, solo_audio=not video))
        if len(audios) > 1:
            base['audios'] = _nombres_audio(audios[:16])
    # subtítulos: archivos .vtt/.srt junto al video y pistas incrustadas
    carpeta, raiz = os.path.dirname(ruta), os.path.splitext(os.path.basename(ruta))[0]
    try:
        for nombre in sorted(os.listdir(carpeta)):
            if nombre.startswith(raiz) and nombre.lower().endswith(('.vtt', '.srt')):
                partes = nombre[len(raiz):].strip('.').split('.')
                idioma = partes[0] if len(partes) > 1 else ''
                base['subtitulos'].append({'idioma': idioma, 'nombre': idioma or nombre,
                                           'src': proxy.subtitulos(ruta=os.path.join(carpeta, nombre))})
    except OSError:
        pass
    for n, idioma, titulo_pista in pistas[:12]:
        base['subtitulos'].append({'idioma': idioma or '', 'nombre': titulo_pista or idioma or f'Pista {n + 1}',
                                   'src': proxy.subtitulos(ruta=ruta, pista=n)})
    return base


# ---------- torrents ----------
def resolver_torrent(origen, torrents, proxy, ffprobe):
    """Abre el torrent (solo el video más grande, en orden) y lo prepara para el reproductor."""
    from .ver_torrent import TorrentNoReproducible
    try:
        clave = torrents.abrir(origen)
    except TorrentNoReproducible as e:
        raise NoReproducible(str(e)) from None
    t = torrents.datos(clave)
    url = proxy.torrent(torrents, clave)
    ext = os.path.splitext(t['nombre'])[1].lower()
    if ext in ('.mp4', '.m4v', '.webm', '.mp3', '.m4a', '.ogg', '.opus', '.flac', '.wav'):
        video, audio, duracion = ext not in ('.mp3', '.m4a', '.ogg', '.opus', '.flac', '.wav') and 'avc1', None, None
    else:   # mkv, avi…: hay que saber el códec para copiarlo o convertirlo (lee la cabecera a través del proxy)
        video, audio, duracion, _, _ = sondear(url, ffprobe, espera=25)
        video = video or 'h264'   # si no responde a tiempo, se intenta copiar
    datos = {'titulo': os.path.splitext(t['nombre'])[0], 'canal': t['titulo'] if t['titulo'] != t['nombre'] else None,
             'duracion': duracion, 'miniatura': None, 'origen': origen, 'solo_audio': not video, 'torrent': clave,
             'subtitulos': [{'idioma': '', 'nombre': os.path.basename(s), 'src': proxy.subtitulos(ruta=s)} for s in t['subs']]}
    if (ext in EXT_DIRECTAS and (not video or _compatible(video, VIDEO_COMPATIBLE))
            and (not audio or _compatible(audio, AUDIO_COMPATIBLE))):
        datos.update(modo='directo', src=url)
    else:
        transcodificar = bool(video) and not _compatible(video, VIDEO_COMPATIBLE)
        datos.update(modo='remux', src=proxy.remux([(url, None)], transcodificar=transcodificar, solo_audio=not video))
    return datos


# ---------- enlaces ----------
def _pista_vtt(formatos):
    """YouTube da dos «vtt» para los automáticos: uno es una lista HLS por trozos (m3u8_native) y el otro el archivo
    entero. Se prefiere el entero (el proxy también sabe juntar los trozos si solo hay ese)."""
    vtts = [f for f in formatos or [] if f.get('ext') == 'vtt' and f.get('url')]
    return next((f for f in vtts if 'm3u8' not in str(f.get('protocol') or '')), vtts[0] if vtts else None)


def _subtitulos_de(info, proxy, maximo=160):
    """Subtítulos para el menú de Ver, en este orden: los del autor del video, los automáticos en el idioma original
    y las traducciones automáticas de YouTube (español e inglés primero, luego el resto por nombre).
    El VTT de cada uno solo se descarga al elegirlo."""
    lista, vistos = [], set()
    preferencia = lambda codigo, f: (codigo.split('-')[0] not in IDIOMAS_PREFERIDOS,
                                     str((_pista_vtt(f) or {}).get('name') or codigo).lower())

    def agregar(codigo, formatos, sufijo):
        base = codigo.split('-')[0]
        pista = _pista_vtt(formatos)
        if codigo == 'live_chat' or base in vistos or not pista or len(lista) >= maximo:
            return
        vistos.add(base)
        lista.append({'idioma': codigo, 'nombre': (pista.get('name') or codigo) + sufijo,
                      'src': proxy.subtitulos(url=pista['url'], cabeceras=pista.get('http_headers'))})

    manuales = info.get('subtitles') or {}
    for codigo in sorted(manuales, key=lambda c: preferencia(c, manuales[c])):
        agregar(codigo, manuales[codigo], '')
    automaticos = info.get('automatic_captions') or {}
    originales = [c for c in automaticos if c.endswith('-orig')]
    for codigo in originales:
        agregar(codigo, automaticos[codigo], ' (automáticos)')
    resto = [c for c in automaticos if not c.endswith('-orig')]
    for codigo in sorted(resto, key=lambda c: preferencia(c, automaticos[c])):
        agregar(codigo, automaticos[codigo], ' (traducción automática)' if originales else ' (automáticos)')
    return lista


def _audio_original(f):
    """YouTube con doblajes: la pista original lleva language_preference alto o «original» en la nota."""
    nota = f'{f.get("format_note") or ""} {f.get("format") or ""}'.lower()
    return ('original' in nota) + ((f.get('language_preference') or 0) >= 10) - ('dubbed' in nota or 'doblado' in nota)


def elegir_fuente(info, url, referer=None):
    """Elige cómo reproducir a partir del info de yt-dlp. Devuelve (modo, datos) sin tocar la red."""
    formatos = info.get('formats') or [info]
    # 1. HLS: maestro de YouTube (manifest_url) o un .m3u8 directo
    hls = [f for f in formatos if f.get('protocol') in ('m3u8_native', 'm3u8') and (f.get('manifest_url') or f.get('url'))
           and f.get('vcodec') != 'none']
    if hls:
        maestro = next((f['manifest_url'] for f in hls if f.get('manifest_url')), None) or hls[-1]['url']
        cab = dict(hls[-1].get('http_headers') or {})
        if referer:
            cab['Referer'] = referer
        return 'hls', {'url': maestro, 'cabeceras': cab}
    # 2. progresivo con audio y video compatibles
    combinados = [f for f in formatos if f.get('protocol') in ('https', 'http') and f.get('url')
                  and _compatible(f.get('vcodec'), VIDEO_COMPATIBLE) and _compatible(f.get('acodec'), AUDIO_COMPATIBLE)
                  and f.get('ext') in ('mp4', 'webm', 'm4v', 'mov')]
    if combinados:
        f = max(combinados, key=lambda f: ((f.get('height') or 0) <= 1080, f.get('height') or 0, f.get('tbr') or 0))
        return 'directo', {'url': f['url'], 'cabeceras': f.get('http_headers') or {}}
    # 3. video y audio separados → remux con ffmpeg
    videos = [f for f in formatos if f.get('url') and _compatible(f.get('vcodec'), VIDEO_COMPATIBLE)
              and f.get('acodec') in (None, 'none') and f.get('protocol') in ('https', 'http', 'http_dash_segments', None)]
    audios = [f for f in formatos if f.get('url') and f.get('vcodec') in (None, 'none')
              and _compatible(f.get('acodec'), AUDIO_COMPATIBLE) and f.get('protocol') in ('https', 'http', None)]
    if videos and audios:
        v = max(videos, key=lambda f: ((f.get('height') or 0) <= 1080, f.get('vcodec', '').startswith('avc1'),
                                       f.get('height') or 0, f.get('tbr') or 0))
        orden = lambda f: (_audio_original(f), f.get('acodec', '').startswith('mp4a'), f.get('abr') or f.get('tbr') or 0)
        # la mejor de cada idioma (doblajes); la original primero
        por_idioma = {}
        for f in audios:
            clave = (f.get('language') or '').lower()
            if clave not in por_idioma or orden(f) > orden(por_idioma[clave]):
                por_idioma[clave] = f
        elegidas = sorted(por_idioma.values(), key=orden, reverse=True)[:24]
        a = elegidas[0]
        datos = {'entradas': [(v['url'], v.get('http_headers')), (a['url'], a.get('http_headers'))]}
        if len(elegidas) > 1:
            datos['audios'] = [(f['url'], f.get('http_headers')) for f in elegidas]
            datos['nombres_audio'] = [{'idioma': (f.get('language') or '').lower(), 'original': _audio_original(f) > 0,
                                       'nombre': f.get('format_note') or f.get('language') or f'Pista {n + 1}'}
                                      for n, f in enumerate(elegidas)]
        return 'remux', datos
    solos = [f for f in formatos if f.get('url') and _compatible(f.get('acodec'), AUDIO_COMPATIBLE)
             and f.get('vcodec') in (None, 'none') and f.get('protocol') in ('https', 'http')]
    if solos:
        a = max(solos, key=lambda f: (_audio_original(f), f.get('abr') or f.get('tbr') or 0))
        return 'directo-audio', {'url': a['url'], 'cabeceras': a.get('http_headers') or {}}
    if es_manifiesto(url) == 'mpd' or info.get('url'):
        return 'remux', {'entradas': [(info.get('url') or url, {'Referer': referer} if referer else None)]}
    raise NoReproducible('No se encontró un formato que se pueda reproducir aquí. Prueba a descargarlo.')


def resolver_enlace(url, proxy, opciones_ytdlp, referer=None):
    import yt_dlp
    if es_manifiesto(url) and not referer:
        referer = referer_desde(url)
    opciones = dict(opciones_ytdlp, noplaylist=True, skip_download=True)
    if referer:
        opciones['http_headers'] = {**(opciones.get('http_headers') or {}), 'Referer': referer}
    with yt_dlp.YoutubeDL(opciones) as ydl:
        info = ydl.sanitize_info(ydl.extract_info(url, download=False))
    if info.get('_type') in ('playlist', 'multi_video'):
        raise NoReproducible('Es una playlist: ábrela con «Ver» desde una colección o el stack, o elige un video.')
    if info.get('is_live'):
        pass   # los directos en HLS se reproducen igual
    modo, datos = elegir_fuente(info, url, referer)
    if modo == 'hls':
        src = proxy.hls(datos['url'], datos['cabeceras'])
    elif modo in ('directo', 'directo-audio'):
        src = proxy.directo(datos['url'], datos['cabeceras'])
    else:
        src = proxy.remux(datos['entradas'], audios=datos.get('audios'))
    return {
        'modo': 'directo' if modo == 'directo-audio' else modo, 'src': src, 'solo_audio': modo == 'directo-audio',
        'titulo': info.get('title') or url, 'canal': info.get('channel') or info.get('uploader'),
        'duracion': info.get('duration'), 'miniatura': info.get('thumbnail'), 'origen': url,
        'en_vivo': bool(info.get('is_live')), 'subtitulos': _subtitulos_de(info, proxy),
        'audio_original': idioma_original(info),
        'audios': datos.get('nombres_audio'),   # pistas para elegir cuando el audio va aparte (remux)
    }


def idioma_original(info):
    """Idioma del audio original (YouTube marca la pista original con language_preference 10)."""
    mejor = max((f for f in info.get('formats') or [] if f.get('acodec') not in (None, 'none') and f.get('language')),
                key=lambda f: f.get('language_preference') or -1, default=None)
    if mejor and (mejor.get('language_preference') or -1) >= 10:
        return str(mejor['language'])
    return None


# ---------- vistos recientemente ----------
def _ruta_vistos():
    return os.path.join(carpeta_datos(), 'vistos.json')


def leer_vistos():
    try:
        with open(_ruta_vistos(), 'r', encoding='utf-8') as f:
            datos = json.load(f)
        return datos if isinstance(datos, list) else []
    except (OSError, ValueError):
        return []


def anotar_visto(entrada):
    """Guarda en 'Vistos recientemente' (sin tokens en las URLs). entrada: {origen, titulo, miniatura, duracion}."""
    origen = str(entrada.get('origen') or '')
    if not origen:
        return
    es_local = not origen.lower().startswith(('http://', 'https://', 'magnet:'))
    limpio = {'origen': origen if es_local else ocultar_tokens(origen), 'titulo': str(entrada.get('titulo') or '')[:300],
              'miniatura': entrada.get('miniatura') if str(entrada.get('miniatura') or '').startswith('https://') else None,
              'duracion': entrada.get('duracion'), 'cuando': time.time(), 'local': es_local}
    if limpio['origen'].lower().startswith('magnet:') or '***' in limpio['origen']:
        return   # enlaces con token caducan: no tiene sentido guardarlos
    vistos = [v for v in leer_vistos() if v.get('origen') != limpio['origen']]
    vistos.insert(0, limpio)
    temporal = _ruta_vistos() + '.tmp'
    try:
        with open(temporal, 'w', encoding='utf-8') as f:
            json.dump(vistos[:MAX_VISTOS], f, ensure_ascii=False)
        os.replace(temporal, _ruta_vistos())
    except OSError:
        pass
