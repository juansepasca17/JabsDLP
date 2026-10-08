"""Una descarga: opciones de yt-dlp, progreso, postprocesos y recodificación con la GPU."""
import glob
import os
import re
import threading
import time
import uuid

import yt_dlp
from yt_dlp.postprocessor import EmbedThumbnailPP, FFmpegEmbedSubtitlePP, FFmpegExtractAudioPP, FFmpegMetadataPP
from yt_dlp.postprocessor.common import PostProcessor
from yt_dlp.utils import sanitize_filename

from .cookies import borrar_temporal, opciones_cookies
from .formatos import NOMBRE_VIDEO, familia_audio, necesita_recodificar, selector_por_preferencias, tamano
from .utilidades import Cancelado, error_amigable, runtimes_js

FASES_PP = {
    'Merger': 'Uniendo video y audio',
    'ExtractAudio': 'Extrayendo audio',
    'FFmpegExtractAudio': 'Extrayendo audio',
    'Metadata': 'Añadiendo metadatos',
    'FFmpegMetadata': 'Añadiendo metadatos',
    'EmbedThumbnail': 'Incrustando miniatura',
    'EmbedSubtitle': 'Incrustando subtítulos',
    'FFmpegEmbedSubtitle': 'Incrustando subtítulos',
    'FixupM4a': 'Reparando contenedor',
    'FixupM3u8': 'Reparando contenedor',
}
TERMINADOS = ('completado', 'error', 'cancelado')
EXT_SUELTOS = ('.webp', '.jpg', '.jpeg', '.png', '.*.vtt', '.*.srt', '.*.ass', '.temp.*', '.part')
EXT_CON_MINIATURA = ('mp3', 'mkv', 'mka', 'ogg', 'opus', 'flac', 'm4a', 'mp4', 'm4v', 'mov')


class Trabajo:
    def __init__(self, url, prefs, titulo=None, miniatura=None, canal=None, duracion=None, formato=None,
                 contenedor=None, titulo_formato=None, tamano=None, subcarpeta=None):
        self.id = uuid.uuid4().hex[:12]
        self.url = url
        self.prefs = dict(prefs)
        self.titulo = titulo or url
        self.miniatura = miniatura
        self.canal = canal
        self.duracion = duracion
        self.formato = formato
        self.contenedor = contenedor
        self.titulo_formato = titulo_formato
        self.tamano = tamano
        self.subcarpeta = subcarpeta
        self.creado = time.time()
        self.registro = []
        self.proceso = None
        self._cancelar = threading.Event()
        self.reiniciar()

    def reiniciar(self):
        self.estado = 'en_cola'
        self.fase = ''
        self.progreso = 0.0
        self.descargado = 0
        self.total = self.tamano
        self.velocidad = None
        self.eta = None
        self.progreso_conversion = 0.0
        self.velocidad_conversion = None
        self.encoder = None
        self.error = None
        self.aviso = None
        self.archivo = None
        self.terminado = None
        self._temporales = set()
        self._bases = set()
        self._cancelar.clear()

    @property
    def cancelado(self):
        return self._cancelar.is_set()

    def cancelar(self):
        self._cancelar.set()
        proceso = self.proceso
        if proceso is not None:
            try:
                proceso.kill()
            except OSError:
                pass

    def a_dict(self):
        return {
            'id': self.id, 'url': self.url, 'titulo': self.titulo, 'miniatura': self.miniatura, 'canal': self.canal,
            'duracion': self.duracion, 'titulo_formato': self.titulo_formato, 'tipo': self.prefs.get('tipo'),
            'estado': self.estado, 'fase': self.fase, 'progreso': round(self.progreso, 4),
            'descargado': self.descargado, 'total': self.total, 'velocidad': self.velocidad, 'eta': self.eta,
            'progreso_conversion': round(self.progreso_conversion, 4), 'velocidad_conversion': self.velocidad_conversion,
            'encoder': self.encoder, 'error': self.error, 'aviso': self.aviso, 'archivo': self.archivo,
            'creado': self.creado, 'terminado': self.terminado,
            'prefs': self.prefs, 'formato': self.formato, 'contenedor': self.contenedor, 'tamano': self.tamano,
            'subcarpeta': self.subcarpeta,
        }

    @classmethod
    def desde_dict(cls, d):
        t = cls(d['url'], d.get('prefs') or {}, d.get('titulo'), d.get('miniatura'), d.get('canal'), d.get('duracion'),
                d.get('formato'), d.get('contenedor'), d.get('titulo_formato'), d.get('tamano'), d.get('subcarpeta'))
        t.id = d.get('id') or t.id
        t.creado = d.get('creado') or t.creado
        t.estado = d.get('estado') if d.get('estado') in TERMINADOS else 'cancelado'
        t.progreso = 1.0 if t.estado == 'completado' else d.get('progreso') or 0.0
        t.archivo, t.error, t.aviso = d.get('archivo'), d.get('error'), d.get('aviso')
        t.encoder, t.terminado, t.total = d.get('encoder'), d.get('terminado'), d.get('total')
        return t


class Registro:
    """Logger para yt-dlp: guarda las últimas líneas en el trabajo (nunca contenido de cookies)."""

    def __init__(self, trabajo):
        self._t = trabajo

    def _agregar(self, nivel, msg):
        self._t.registro.append(f'[{nivel}] {msg}')
        del self._t.registro[:-60]

    def debug(self, msg):
        if not msg.startswith('[debug] '):
            self._agregar('info', msg)

    def info(self, msg):
        self._agregar('info', msg)

    def warning(self, msg):
        self._agregar('aviso', msg)

    def error(self, msg):
        self._agregar('error', msg)


class RecodificarPP(PostProcessor):
    """Convierte a H.265/H.264 con la GPU (o CPU) cuando el códec descargado no es el preferido."""

    def __init__(self, downloader, trabajo, herramientas):
        super().__init__(downloader)
        self._t = trabajo
        self._herr = herramientas

    def run(self, info):
        objetivo = necesita_recodificar(info.get('vcodec'), self._t.prefs)
        entrada = info.get('filepath')
        if not objetivo or not entrada or not os.path.exists(entrada):
            return [], info
        base, ext = os.path.splitext(entrada)
        ext_salida = ext if ext.lower() in ('.mp4', '.mkv', '.mov') else '.mkv'
        temporal = f'{base}.recodificando{ext_salida}'
        self._t.estado = 'esperando_gpu'
        self._t.fase = 'Esperando turno para convertir'
        self._herr.conversiones.entrar(self._t)
        try:
            self._t.estado = 'convirtiendo'
            self._t.fase = f'Convirtiendo a {NOMBRE_VIDEO[objetivo]}'
            self._t.progreso_conversion = 0.0
            copiar_audio = not (ext_salida == '.mp4' and familia_audio(info.get('acodec')) in ('vorbis', 'otro'))
            self._herr.recodificar(entrada, temporal, objetivo, info.get('duration'), self._t, copiar_audio)
        finally:
            self._herr.conversiones.salir()
        final = base + ext_salida
        os.replace(temporal, final)
        if final != entrada:
            os.unlink(entrada)
        info['filepath'] = final
        info['ext'] = ext_salida[1:]
        info['vcodec'] = 'hvc1' if objetivo == 'h265' else 'avc1'
        self._t.estado = 'procesando'
        return [], info


def _contenedor_merge(trabajo):
    if trabajo.contenedor:
        return trabajo.contenedor
    # yt-dlp no considera Opus compatible con MP4 y elegiría MKV; ffmpeg sí lo admite, así que Auto = MP4
    preferido = trabajo.prefs.get('contenedor', 'auto')
    return {'webm': 'webm/mkv', 'mkv': 'mkv'}.get(preferido, 'mp4')


def _ganchos(trabajo):
    def progreso(d):
        if trabajo.cancelado:
            raise Cancelado()
        info = d.get('info_dict') or {}
        if trabajo.titulo == trabajo.url and info.get('title'):
            trabajo.titulo = info['title']
        if not trabajo.miniatura and info.get('thumbnail'):
            trabajo.miniatura = info['thumbnail']
        if not trabajo.canal:
            trabajo.canal = info.get('channel') or info.get('uploader')
        if d.get('tmpfilename'):
            trabajo._temporales.add(d['tmpfilename'])
        if d.get('filename'):
            trabajo._temporales.add(d['filename'] + '.ytdl')
            base = os.path.splitext(d['filename'])[0]
            trabajo._bases.add(re.sub(r'\.f[\w-]+$', '', base))
        if d['status'] == 'downloading':
            trabajo.estado = 'descargando'
            partes = info.get('requested_formats') or [info]
            ids = [p.get('format_id') for p in partes]
            indice = ids.index(info.get('format_id')) if info.get('format_id') in ids else 0
            duracion = info.get('duration')
            pesos = [tamano(p, duracion) or 0 for p in partes]
            total_parte = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            if total_parte:
                pesos[indice] = total_parte
            conocidos = [p for p in pesos if p]
            relleno = sum(conocidos) / len(conocidos) if conocidos else 1
            pesos = [p or relleno for p in pesos]
            fraccion = (d.get('downloaded_bytes') or 0) / total_parte if total_parte else 0
            trabajo.progreso = min(0.999, (sum(pesos[:indice]) + fraccion * pesos[indice]) / sum(pesos))
            trabajo.total = int(sum(pesos)) if total_parte else trabajo.total
            trabajo.descargado = int(sum(pesos[:indice]) + (d.get('downloaded_bytes') or 0))
            trabajo.velocidad = d.get('speed')
            trabajo.eta = d.get('eta')
            if len(partes) > 1:
                tipo = 'video' if partes[indice].get('vcodec') not in (None, 'none') else 'audio'
                trabajo.fase = f'Descargando {tipo} ({indice + 1}/{len(partes)})'
            else:
                trabajo.fase = 'Descargando'
        elif d['status'] == 'finished':
            trabajo.velocidad = None
            trabajo.eta = None

    def postproceso(d):
        if trabajo.cancelado:
            raise Cancelado()
        if d.get('status') == 'started':
            nombre = d.get('postprocessor') or ''
            if nombre in FASES_PP and trabajo.estado != 'convirtiendo':
                trabajo.estado = 'procesando'
                trabajo.fase = FASES_PP[nombre]

    return progreso, postproceso


def _limpiar_temporales(trabajo):
    """Borra .part, fragmentos, .ytdl y la miniatura/subtítulos sueltos de una descarga cancelada."""
    rutas = set()
    for temporal in trabajo._temporales:
        rutas.update(glob.glob(glob.escape(temporal) + '*'))
    for base in trabajo._bases:
        for ext in EXT_SUELTOS:
            rutas.update(glob.glob(glob.escape(base) + ext))
    for ruta in rutas:
        try:
            os.unlink(ruta)
        except OSError:
            pass


def ejecutar(trabajo, ajustes, herramientas):
    prefs = trabajo.prefs
    audio = prefs.get('tipo') == 'audio'
    carpeta = ajustes.carpeta()
    if trabajo.subcarpeta and ajustes.get('subcarpeta_playlist'):
        carpeta = os.path.join(carpeta, sanitize_filename(trabajo.subcarpeta, restricted=False))
    progreso, postproceso = _ganchos(trabajo)
    cookies_tmp = None
    trabajo.estado = 'iniciando'
    trabajo.fase = 'Preparando'
    try:
        os.makedirs(carpeta, exist_ok=True)
        opciones = {
            'outtmpl': os.path.join(carpeta, ajustes.get('plantilla') or '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'noprogress': True,
            'noplaylist': True,
            'windowsfilenames': True,
            'concurrent_fragment_downloads': max(1, int(ajustes.get('fragmentos') or 4)),
            'retries': 10,
            'fragment_retries': 10,
            'logger': Registro(trabajo),
            'progress_hooks': [progreso],
            'postprocessor_hooks': [postproceso],
        }
        runtimes = runtimes_js()
        if runtimes:
            opciones['js_runtimes'] = runtimes
        ffmpeg = herramientas.ffmpeg()
        if ffmpeg:
            opciones['ffmpeg_location'] = os.path.dirname(ffmpeg)
        if trabajo.formato:
            opciones['format'] = trabajo.formato
        else:
            opciones['format'], opciones['format_sort'] = selector_por_preferencias(prefs)
        if not audio:
            opciones['merge_output_format'] = _contenedor_merge(trabajo)

        con_metadatos = prefs.get('metadatos', True)
        con_miniatura = con_metadatos and prefs.get('miniatura', True) and \
            (audio or _contenedor_merge(trabajo).split('/')[0] != 'webm')
        con_subtitulos = not audio and prefs.get('subtitulos')
        if con_miniatura:
            opciones['writethumbnail'] = True
        if con_subtitulos:
            opciones['writesubtitles'] = True
            opciones['subtitleslangs'] = [s.strip() for s in (ajustes.get('idiomas_subtitulos') or 'es.*').split(',') if s.strip()]

        extra_cookies, cookies_tmp = opciones_cookies(ajustes)
        opciones.update(extra_cookies)

        with yt_dlp.YoutubeDL(opciones) as ydl:
            if audio:
                formato_audio = prefs.get('formato_audio', 'auto')
                ydl.add_post_processor(FFmpegExtractAudioPP(
                    ydl, preferredcodec=None if formato_audio == 'auto' else formato_audio, preferredquality='0'))
            else:
                ydl.add_post_processor(RecodificarPP(ydl, trabajo, herramientas))
                if con_subtitulos:
                    ydl.add_post_processor(FFmpegEmbedSubtitlePP(ydl, already_have_subtitle=False))
            if con_metadatos:
                ydl.add_post_processor(FFmpegMetadataPP(ydl, add_metadata=True, add_chapters=True, add_infojson=False))
            if con_miniatura:
                ydl.add_post_processor(MiniaturaSeguraPP(ydl))
            ydl.add_post_hook(lambda ruta: setattr(trabajo, 'archivo', ruta))
            info = ydl.extract_info(trabajo.url, download=True)

        if trabajo.cancelado:
            raise Cancelado()
        if not trabajo.archivo:
            descargas = (info or {}).get('requested_downloads') or [{}]
            trabajo.archivo = descargas[-1].get('filepath') or (info or {}).get('filepath')
        if trabajo.archivo and os.path.exists(trabajo.archivo):
            trabajo.total = trabajo.descargado = os.path.getsize(trabajo.archivo)
        trabajo.estado = 'completado'
        trabajo.fase = 'Completado'
        trabajo.progreso = 1.0
    except Exception as e:  # noqa: BLE001 - cualquier fallo se muestra en la tarjeta
        if trabajo.cancelado or isinstance(e, Cancelado):
            trabajo.estado = 'cancelado'
            trabajo.fase = 'Cancelado'
            _limpiar_temporales(trabajo)
        else:
            trabajo.estado = 'error'
            trabajo.fase = 'Error'
            trabajo.error = error_amigable(e)
    finally:
        borrar_temporal(cookies_tmp)
        trabajo.velocidad = None
        trabajo.eta = None
        trabajo.terminado = time.time()


class MiniaturaSeguraPP(EmbedThumbnailPP):
    """Incrusta la miniatura solo en contenedores que la admiten; si falla, no tumba la descarga."""

    def __init__(self, downloader):
        super().__init__(downloader, already_have_thumbnail=False)

    def run(self, info):
        if info.get('ext') not in EXT_CON_MINIATURA:
            return [thumb.get('filepath') for thumb in info.get('thumbnails') or [] if thumb.get('filepath')], info
        try:
            return super().run(info)
        except Exception as e:  # noqa: BLE001
            self.report_warning(f'No se pudo incrustar la miniatura: {e}')
            return [thumb.get('filepath') for thumb in info.get('thumbnails') or [] if thumb.get('filepath')], info
