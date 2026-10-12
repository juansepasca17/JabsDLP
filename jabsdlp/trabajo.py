"""Una descarga: opciones de yt-dlp, progreso, postprocesos y recodificación con la GPU."""
import glob
import os
import re
import threading
import time
import uuid

import yt_dlp
from yt_dlp.postprocessor import (EmbedThumbnailPP, FFmpegEmbedSubtitlePP, FFmpegExtractAudioPP, FFmpegMetadataPP,
                                  ModifyChaptersPP, SponsorBlockPP)
from yt_dlp.postprocessor.common import PostProcessor
from yt_dlp.utils import sanitize_filename

from . import aria2
from .ajustes import carpeta_datos
from .argumentos import interpretar
from .cookies import borrar_temporal, opciones_cookies
from .formatos import NOMBRE_VIDEO, familia_audio, necesita_recodificar, normalizar, selector_por_preferencias, tamano
from .sponsor import categorias_validas
from .utilidades import Cancelado, clasificar_error, runtimes_js

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
    'SponsorBlock': 'Buscando anuncios (SponsorBlock)',
    'ModifyChapters': 'Quitando anuncios',
}
TERMINADOS = ('completado', 'error', 'cancelado', 'omitido')
PENDIENTES = ('en_cola', 'iniciando', 'descargando', 'procesando', 'esperando_gpu', 'convirtiendo', 'reintentando',
              'pausado')
EXT_SUELTOS = ('.webp', '.jpg', '.jpeg', '.png', '.*.vtt', '.*.srt', '.*.ass', '.temp.*', '.part')
EXT_CON_MINIATURA = ('mp3', 'mkv', 'mka', 'ogg', 'opus', 'flac', 'm4a', 'mp4', 'm4v', 'mov')
CAMPOS_GUARDADOS = ('url', 'prefs', 'titulo', 'miniatura', 'canal', 'duracion', 'formato', 'contenedor',
                    'titulo_formato', 'tamano', 'subcarpeta', 'grupo_id', 'indice', 'total_grupo', 'recorte',
                    'quitar_anuncios')


def ruta_archivo_descargados():
    return os.path.join(carpeta_datos(), 'descargados.txt')


def _segundos_a_texto(segundos):
    s = int(round(segundos))
    h, m, s = s // 3600, s % 3600 // 60, s % 60
    return (f'{h}h' if h else '') + (f'{m}m' if m or h else '') + f'{s}s'


class Trabajo:
    def __init__(self, url, prefs, titulo=None, miniatura=None, canal=None, duracion=None, formato=None,
                 contenedor=None, titulo_formato=None, tamano=None, subcarpeta=None, grupo_id=None, indice=None,
                 total_grupo=None, recorte=None, quitar_anuncios=False):
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
        self.grupo_id = grupo_id            # trabajos de una misma playlist o lote
        self.indice = indice                # posición en la playlist (para numerar)
        self.total_grupo = total_grupo
        self.recorte = list(recorte) if recorte else None   # [inicio, fin] en segundos
        self.quitar_anuncios = bool(quitar_anuncios)
        self.creado = time.time()
        self.registro = []
        self.proceso = None
        self.intentos = 0                   # reintentos automáticos ya hechos
        self.motor_forzado = None           # 'aria2' cuando el reintento automático cambia de motor
        self._cancelar = threading.Event()
        self.pausar = False                 # True = se cierra la app: conservar los .part para retomar
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
        self.motor = None
        self.error = None
        self.error_codigo = None
        self.temporal = False
        self.aviso = None
        self.archivo = None
        self.inicio = None
        self.terminado = None
        self.reintento_en = None
        self.omitido = False
        self._temporales = set()
        self._bases = set()
        self._cancelar.clear()
        self.pausar = False

    @property
    def cancelado(self):
        return self._cancelar.is_set()

    def cancelar(self, conservar_parciales=False):
        self.pausar = conservar_parciales
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
            'encoder': self.encoder, 'motor': self.motor, 'error': self.error, 'error_codigo': self.error_codigo,
            'aviso': self.aviso, 'archivo': self.archivo, 'creado': self.creado, 'inicio': self.inicio, 'terminado': self.terminado,
            'intentos': self.intentos, 'reintento_en': self.reintento_en,
            'prefs': self.prefs, 'formato': self.formato, 'contenedor': self.contenedor, 'tamano': self.tamano,
            'subcarpeta': self.subcarpeta, 'grupo_id': self.grupo_id, 'indice': self.indice,
            'total_grupo': self.total_grupo, 'recorte': self.recorte, 'quitar_anuncios': self.quitar_anuncios,
        }

    @classmethod
    def _crear(cls, d):
        t = cls(d['url'], d.get('prefs') or {}, **{k: d.get(k) for k in CAMPOS_GUARDADOS if k not in ('url', 'prefs')})
        t.id = d.get('id') or t.id
        t.creado = d.get('creado') or t.creado
        return t

    @classmethod
    def desde_dict(cls, d):
        """Trabajo terminado del historial."""
        t = cls._crear(d)
        t.estado = d.get('estado') if d.get('estado') in TERMINADOS else 'cancelado'
        t.progreso = 1.0 if t.estado == 'completado' else d.get('progreso') or 0.0
        t.archivo, t.error, t.aviso = d.get('archivo'), d.get('error'), d.get('aviso')
        t.error_codigo, t.motor = d.get('error_codigo'), d.get('motor')
        t.encoder, t.terminado, t.total = d.get('encoder'), d.get('terminado'), d.get('total')
        t.inicio = d.get('inicio')
        return t

    @classmethod
    def pendiente_desde_dict(cls, d):
        """Trabajo que quedó a medias al cerrar la app: vuelve a la cola (yt-dlp continúa el .part)."""
        t = cls._crear(d)
        t.aviso = 'Retomado tras cerrar la app'
        return t


class Registro:
    """Logger para yt-dlp: guarda las últimas líneas en el trabajo (nunca contenido de cookies)."""

    def __init__(self, trabajo):
        self._t = trabajo

    def _agregar(self, nivel, msg):
        if 'has already been recorded in the archive' in msg:
            self._t.omitido = True
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


class RecortarPP(PostProcessor):
    """Recorta el tramo elegido en el equipo con ffmpeg (YouTube no deja leer solo un tramo con ffmpeg).

    Sin "corte exacto" copia los streams (instantáneo, empieza en el fotograma clave anterior);
    con "corte exacto" recodifica el video (GPU si hay) para cortar en el fotograma justo.
    """

    def __init__(self, downloader, trabajo, herramientas, exacto):
        super().__init__(downloader)
        self._t = trabajo
        self._herr = herramientas
        self._exacto = exacto

    def run(self, info):
        import subprocess
        from .utilidades import SIN_VENTANA
        entrada = info.get('filepath')
        ffmpeg = self._herr.ffmpeg()
        if not self._t.recorte or not entrada or not os.path.exists(entrada) or not ffmpeg:
            return [], info
        inicio, fin = self._t.recorte
        base, ext = os.path.splitext(entrada)
        temporal = f'{base}.recortando{ext}'
        self._t.estado = 'procesando'
        self._t.fase = 'Recortando el tramo'
        comando = [ffmpeg, '-hide_banner', '-nostdin', '-y', '-loglevel', 'error', '-ss', f'{inicio:.3f}', '-i', entrada,
                   '-t', f'{fin - inicio:.3f}', '-map', '0', '-map_metadata', '0']
        es_video = info.get('vcodec') not in (None, 'none')
        if self._exacto and es_video:
            tipo = self._herr.tipo_encoder()
            comando += self._herr._args_video(tipo, 'h264')
            comando += ['-c:a', 'copy', '-c:s', 'copy']
            if ext == '.webm':  # H.264 no cabe en WEBM
                temporal = f'{base}.recortando.mkv'
        else:
            comando += ['-c', 'copy', '-avoid_negative_ts', 'make_zero']
        comando.append(temporal)
        proc = subprocess.run(comando, capture_output=True, text=True, encoding='utf-8', errors='replace',
                              creationflags=SIN_VENTANA)
        if proc.returncode != 0 or not os.path.exists(temporal):
            raise RuntimeError(f'No se pudo recortar el video: {proc.stderr.strip()[-200:]}')
        final = os.path.splitext(temporal.replace('.recortando', ''))[0] + os.path.splitext(temporal)[1]
        os.replace(temporal, final)
        if os.path.normcase(final) != os.path.normcase(entrada):
            os.unlink(entrada)
        info['filepath'] = final
        info['ext'] = os.path.splitext(final)[1][1:]
        info['duration'] = fin - inicio
        return [], info


def _contenedor_merge(trabajo):
    if trabajo.contenedor:
        return trabajo.contenedor
    # yt-dlp no considera Opus compatible con MP4 y elegiría MKV; ffmpeg sí lo admite, así que Auto = MP4
    preferido = trabajo.prefs.get('contenedor', 'auto')
    return {'webm': 'webm/mkv', 'mkv': 'mkv'}.get(preferido, 'mp4')


def plantilla_salida(plantilla, trabajo, numerar):
    """Añade '01 - ' (playlist numerada) y ' [1m20s-3m45s]' (recorte) al nombre, sin tocar las carpetas."""
    plantilla = plantilla or '%(title)s.%(ext)s'
    tallo = plantilla[:-len('.%(ext)s')] if plantilla.endswith('.%(ext)s') else plantilla
    carpeta, nombre = os.path.split(tallo.replace('\\', '/'))
    if numerar and trabajo.indice:
        ancho = max(2, len(str(trabajo.total_grupo or trabajo.indice)))
        nombre = f'{int(trabajo.indice):0{ancho}d} - {nombre}'
    if trabajo.recorte:
        inicio, fin = trabajo.recorte
        nombre += f' [{_segundos_a_texto(inicio)}-{_segundos_a_texto(fin)}]'
    return (f'{carpeta}/{nombre}' if carpeta else nombre) + '.%(ext)s'


def _ganchos(trabajo, cubeta):
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
        clave = d.get('tmpfilename') or d.get('filename') or trabajo.id
        if d['status'] == 'downloading':
            trabajo.estado = 'descargando'
            if cubeta is not None and trabajo.motor != 'aria2':
                cubeta.consumir(cubeta.bytes_nuevos(clave, d.get('downloaded_bytes') or 0))
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
            if cubeta is not None:
                cubeta.olvidar(clave)

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


def _idiomas_subtitulos(prefs, ajustes):
    codigos = [c.strip() for c in (prefs.get('idioma_subs') or ajustes.get('idiomas_subtitulos') or 'es').split(',')
               if c.strip()]
    patrones = []
    for c in codigos:
        c = c.replace('.*', '')
        patrones.append(re.escape(c))
        if '-' not in c:
            patrones.append(re.escape(c) + '-.*')  # es -> es-419, es-ES, en -> en-orig...
    return patrones


def _activar_aria2(ajustes, trabajo):
    if not aria2.ruta(ajustes):
        trabajo.aviso = 'aria2 no está instalado (Ajustes → Red); se usó yt-dlp.'
        return False
    carpeta = aria2.carpeta_segura(ajustes)   # None = ya está en el PATH del sistema
    if carpeta and os.path.normcase(carpeta) not in [os.path.normcase(p) for p in os.environ.get('PATH', '').split(os.pathsep)]:
        os.environ['PATH'] = carpeta + os.pathsep + os.environ.get('PATH', '')
    return True


PATRON_ARIA2 = re.compile(r'\[#\w+\s+([\d.]+)(\w+)/([\d.]+)(\w+)\((\d+)%\).*?DL:([\d.]+)(\w+)(?:.*?ETA:(\w+))?')
UNIDADES = {'B': 1, 'KiB': 1024, 'MiB': 1024 ** 2, 'GiB': 1024 ** 3, 'TiB': 1024 ** 4}


def _eta_segundos(texto):
    total = 0
    for numero, unidad in re.findall(r'(\d+)([hms])', texto or ''):
        total += int(numero) * {'h': 3600, 'm': 60, 's': 1}[unidad]
    return total or None


def ejecutar_torrent(trabajo, ajustes, limite_bytes=0):
    """Torrent o magnet con aria2: sin seed al terminar y con la subida limitada."""
    import subprocess
    from .utilidades import SIN_VENTANA
    ruta = aria2.ruta(ajustes)
    if not ruta:
        raise RuntimeError('Los torrents necesitan aria2: instálalo en Ajustes → Red y velocidad.')
    carpeta = ajustes.carpeta()
    os.makedirs(carpeta, exist_ok=True)
    antes = set(os.listdir(carpeta))
    comando = [ruta, *aria2.argumentos_torrent(carpeta, limite_bytes, ajustes.get('subida_torrent_kb') or 20), '--', trabajo.url]
    trabajo.motor = 'aria2'
    trabajo.estado = 'descargando'
    trabajo.fase = 'Conectando con los pares'
    proc = subprocess.Popen(comando, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=SIN_VENTANA,
                            text=True, encoding='utf-8', errors='replace')
    trabajo.proceso = proc
    try:
        for linea in proc.stdout:
            if trabajo.cancelado:
                proc.kill()
                break
            trabajo.registro.append(linea.strip())
            del trabajo.registro[:-60]
            m = PATRON_ARIA2.search(linea)
            if m:
                hecho = float(m.group(1)) * UNIDADES.get(m.group(2), 1)
                total = float(m.group(3)) * UNIDADES.get(m.group(4), 1)
                trabajo.descargado, trabajo.total = int(hecho), int(total) or None
                trabajo.progreso = min(0.999, int(m.group(5)) / 100)
                trabajo.velocidad = float(m.group(6)) * UNIDADES.get(m.group(7), 1)
                trabajo.eta = _eta_segundos(m.group(8))
                trabajo.fase = 'Descargando torrent'
        proc.wait()
    finally:
        trabajo.proceso = None
    if trabajo.cancelado:
        raise Cancelado()
    if proc.returncode != 0:
        ultima = next((l for l in reversed(trabajo.registro) if l), '')
        raise RuntimeError(f'aria2 no pudo descargar el torrent (código {proc.returncode}). {ultima[:200]}')
    nuevos = sorted(set(os.listdir(carpeta)) - antes)
    if nuevos:
        trabajo.archivo = os.path.join(carpeta, nuevos[0])
        if trabajo.titulo == trabajo.url:
            trabajo.titulo = nuevos[0]
    trabajo.estado = 'completado'
    trabajo.fase = 'Completado (sin seed)'
    trabajo.progreso = 1.0


def ejecutar(trabajo, ajustes, herramientas, cubeta=None, limite_aria2=0):
    prefs = normalizar(trabajo.prefs)
    audio = prefs.get('tipo') == 'audio'
    carpeta = ajustes.carpeta()
    if trabajo.subcarpeta and ajustes.get('subcarpeta_playlist'):
        carpeta = os.path.join(carpeta, sanitize_filename(trabajo.subcarpeta, restricted=False))
    progreso, postproceso = _ganchos(trabajo, cubeta)
    cookies_tmp = None
    trabajo.estado = 'iniciando'
    trabajo.fase = 'Preparando'
    trabajo.inicio = time.time()
    try:
        if trabajo.prefs.get('tipo') == 'torrent':
            return ejecutar_torrent(trabajo, ajustes, limite_aria2)
        os.makedirs(carpeta, exist_ok=True)
        plantilla = plantilla_salida(ajustes.get('plantilla'), trabajo, ajustes.get('numerar_playlist'))
        opciones = {
            'outtmpl': os.path.join(carpeta, plantilla),
            'quiet': True,
            'no_warnings': True,
            'noprogress': True,
            'noplaylist': True,
            'windowsfilenames': True,
            'continuedl': True,
            'concurrent_fragment_downloads': max(1, int(ajustes.get('fragmentos') or 4)),
            'retries': 10,
            'fragment_retries': 10,
            'logger': Registro(trabajo),
            'progress_hooks': [progreso],
            'postprocessor_hooks': [postproceso],
        }
        # Comando personalizado (Ajustes → Avanzado): primero, para que las opciones de la app tengan prioridad
        if ajustes.get('args_extra_activo') and ajustes.get('args_extra'):
            extra, pps_extra = interpretar(ajustes.get('args_extra'))
            opciones = {**extra, **opciones}
            if pps_extra:
                opciones['postprocessors'] = pps_extra
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
        if ajustes.get('no_repetir'):
            opciones['download_archive'] = ruta_archivo_descargados()

        motor = trabajo.motor_forzado or ajustes.get('motor')
        trabajo.motor = 'ytdlp'
        # En 'auto' el primer intento es nativo; el reintento llega con motor_forzado='aria2'
        if motor == 'aria2' and aria2.ytdlp_seguro_para_aria2() and _activar_aria2(ajustes, trabajo):
            trabajo.motor = 'aria2'
            # Solo descargas directas (http/https/ftp). HLS y DASH siempre con el motor nativo de yt-dlp:
            # así se evita CVE-2026-50574 (inyección de opciones en aria2c desde manifiestos DASH).
            opciones['external_downloader'] = {'http': 'aria2c', 'ftp': 'aria2c', 'default': 'native'}
            opciones['external_downloader_args'] = {'aria2c': aria2.argumentos(limite_aria2)}

        corte_exacto = bool(ajustes.get('corte_exacto'))

        con_metadatos = prefs.get('metadatos', True)
        con_miniatura = con_metadatos and prefs.get('miniatura', True) and \
            (audio or _contenedor_merge(trabajo).split('/')[0] != 'webm')
        con_subtitulos = not audio and prefs.get('subtitulos')
        if con_miniatura:
            opciones['writethumbnail'] = True
        if con_subtitulos:
            opciones['writesubtitles'] = True
            opciones['writeautomaticsub'] = bool(prefs.get('subs_auto'))
            opciones['subtitleslangs'] = _idiomas_subtitulos(prefs, ajustes)
        categorias = categorias_validas(prefs.get('sponsor_cats')) if trabajo.quitar_anuncios else []
        if categorias and trabajo.recorte:
            categorias = []  # el tramo se eligió sobre el video original: quitar anuncios desplazaría los tiempos
            trabajo.aviso = 'Con un recorte no se quitan anuncios (los tiempos dejarían de coincidir).'

        extra_cookies, cookies_tmp = opciones_cookies(ajustes)
        opciones.update(extra_cookies)

        with yt_dlp.YoutubeDL(opciones) as ydl:
            if categorias:
                ydl.add_post_processor(SponsorBlockPP(ydl, categories=categorias), when='after_filter')
                ydl.add_post_processor(ModifyChaptersPP(ydl, remove_sponsor_segments=categorias,
                                                        force_keyframes=corte_exacto))
            # Orden: subtítulos → recorte (corta también los subtítulos) → recodificar (sobre el tramo, más rápido)
            if audio:
                formato_audio = prefs.get('formato_audio', 'auto')
                ydl.add_post_processor(FFmpegExtractAudioPP(
                    ydl, preferredcodec=None if formato_audio == 'auto' else formato_audio, preferredquality='0'))
                if trabajo.recorte:
                    ydl.add_post_processor(RecortarPP(ydl, trabajo, herramientas, False))
            else:
                if con_subtitulos:
                    ydl.add_post_processor(FFmpegEmbedSubtitlePP(ydl, already_have_subtitle=False))
                if trabajo.recorte:
                    ydl.add_post_processor(RecortarPP(ydl, trabajo, herramientas, corte_exacto))
                ydl.add_post_processor(RecodificarPP(ydl, trabajo, herramientas))
            if con_metadatos:
                ydl.add_post_processor(FFmpegMetadataPP(ydl, add_metadata=True, add_chapters=not trabajo.recorte,
                                                        add_infojson=False))
            if con_miniatura:
                ydl.add_post_processor(MiniaturaSeguraPP(ydl))
            ydl.add_post_hook(lambda ruta: setattr(trabajo, 'archivo', ruta))
            info = ydl.extract_info(trabajo.url, download=True)

        if trabajo.cancelado:
            raise Cancelado()
        if trabajo.omitido and not trabajo.archivo:
            trabajo.estado = 'omitido'
            trabajo.fase = 'Ya descargado'
            trabajo.progreso = 1.0
            return
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
            if trabajo.pausar:
                trabajo.estado = 'pausado'   # se conservan los .part para retomar al reabrir
                trabajo.fase = 'En pausa'
            else:
                trabajo.estado = 'cancelado'
                trabajo.fase = 'Cancelado'
                _limpiar_temporales(trabajo)
        else:
            trabajo.estado = 'error'
            trabajo.fase = 'Error'
            trabajo.error_codigo, trabajo.error, trabajo.temporal = clasificar_error(e)
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
