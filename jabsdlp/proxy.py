"""Proxy local para la pestaña Ver: http://127.0.0.1:<puerto>/<token>/...

El reproductor (WebView2) no puede leer directamente muchos videos remotos: YouTube y otros no envían cabeceras CORS
y algunos exigen Referer o User-Agent concretos. Este servidor, que solo escucha en 127.0.0.1 y exige un token
aleatorio en la ruta, pide los recursos con las cabeceras correctas y los entrega al reproductor:

  /<token>/hls/<id>/<n>.m3u8   manifiesto HLS (las URIs se reescriben para pasar también por aquí)
  /<token>/seg/<id>/<n>        segmento o clave de un HLS
  /<token>/directo/<id>        archivo remoto progresivo (con Range, para saltar en la línea de tiempo)
  /<token>/local/<id>          archivo de tu equipo (con Range)
  /<token>/remux/<id>?t=S      video+audio separados (o formatos no compatibles) unidos con ffmpeg desde el segundo S
  /<token>/subs/<id>/<n>.vtt   subtítulos en WebVTT
  /<token>/torrent/<id>        archivo de un torrent mientras se descarga (con Range; espera las piezas)

Las URLs remotas nunca llegan desde la petición: solo se sirven recursos registrados por la propia app.
"""
import os
import re
import secrets
import subprocess
import threading
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .utilidades import SIN_VENTANA

TIPOS = {'.mp4': 'video/mp4', '.m4v': 'video/mp4', '.webm': 'video/webm', '.mov': 'video/mp4', '.mp3': 'audio/mpeg',
         '.m4a': 'audio/mp4', '.ogg': 'audio/ogg', '.opus': 'audio/ogg', '.oga': 'audio/ogg', '.wav': 'audio/wav',
         '.flac': 'audio/flac', '.aac': 'audio/aac', '.mkv': 'video/x-matroska'}
BLOQUE = 256 * 1024
URI_ATRIBUTO = re.compile(r'URI="([^"]+)"')


class Fuente:
    """Recurso registrado: un HLS (con sus subrecursos), un archivo remoto o local, un remux o subtítulos."""

    def __init__(self, tipo, **datos):
        self.tipo = tipo
        self.datos = datos
        self.recursos = []           # HLS: URLs descubiertas al reescribir manifiestos (índice = n)
        self.lock = threading.Lock()

    def registrar(self, url):
        with self.lock:
            try:
                return self.recursos.index(url)
            except ValueError:
                self.recursos.append(url)
                return len(self.recursos) - 1


class Proxy:
    def __init__(self, ffmpeg=None):
        self.token = secrets.token_urlsafe(18)
        self.fuentes = {}
        self.procesos = set()
        self.ffmpeg = ffmpeg       # función que devuelve la ruta de ffmpeg (o None)
        self._lock = threading.Lock()
        proxy = self

        class Manejador(BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'

            def log_message(self, *args):   # silencioso
                pass

            def do_GET(self):
                proxy._atender(self)

            def do_HEAD(self):
                proxy._atender(self, solo_cabeceras=True)

        self.servidor = ThreadingHTTPServer(('127.0.0.1', 0), Manejador)
        self.servidor.daemon_threads = True
        self.puerto = self.servidor.server_address[1]
        threading.Thread(target=self.servidor.serve_forever, daemon=True, name='proxy-ver').start()

    @property
    def base(self):
        return f'http://127.0.0.1:{self.puerto}/{self.token}'

    # ---------- registro ----------
    def _nuevo(self, fuente):
        id_ = secrets.token_hex(6)
        with self._lock:
            self.fuentes[id_] = fuente
        return id_

    def hls(self, url, cabeceras=None):
        f = Fuente('hls', cabeceras=cabeceras or {})
        id_ = self._nuevo(f)
        f.registrar(url)
        return f'{self.base}/hls/{id_}/0.m3u8'

    def directo(self, url, cabeceras=None):
        return f"{self.base}/directo/{self._nuevo(Fuente('directo', url=url, cabeceras=cabeceras or {}))}"

    def local(self, ruta):
        return f"{self.base}/local/{self._nuevo(Fuente('local', ruta=ruta))}"

    def remux(self, entradas, transcodificar=False, solo_audio=False):
        """entradas: [(url_o_ruta, cabeceras)] (1 o 2: video y audio). Devuelve la URL base (añadir ?t=segundos)."""
        id_ = self._nuevo(Fuente('remux', entradas=entradas, transcodificar=transcodificar, solo_audio=solo_audio))
        return f'{self.base}/remux/{id_}'

    def subtitulos(self, url=None, cabeceras=None, ruta=None, pista=None):
        id_ = self._nuevo(Fuente('subs', url=url, cabeceras=cabeceras or {}, ruta=ruta, pista=pista))
        return f'{self.base}/subs/{id_}/0.vtt'

    def torrent(self, torrents, clave):
        """torrents: objeto con datos(clave) y bloques(clave, inicio, fin, cancelado) (ver_torrent.Torrents)."""
        return f"{self.base}/torrent/{self._nuevo(Fuente('torrent', torrents=torrents, clave=clave))}"

    def olvidar(self):
        """Libera todo lo registrado (al cambiar de video) y mata los ffmpeg en curso."""
        with self._lock:
            self.fuentes.clear()
            procesos, self.procesos = self.procesos, set()
        for p in procesos:
            try:
                p.kill()
            except OSError:
                pass

    def cerrar(self):
        self.olvidar()
        self.servidor.shutdown()

    # ---------- servir ----------
    def _atender(self, h, solo_cabeceras=False):
        partes = urllib.parse.urlsplit(h.path)
        trozos = partes.path.strip('/').split('/')
        if len(trozos) < 3 or not secrets.compare_digest(trozos[0], self.token):
            return self._error(h, 404)
        tipo, id_ = trozos[1], trozos[2]
        fuente = self.fuentes.get(id_)
        if fuente is None or (fuente.tipo != tipo and not (tipo == 'seg' and fuente.tipo == 'hls')):
            return self._error(h, 404)
        try:
            if tipo == 'hls':
                return self._manifiesto(h, fuente, id_, trozos[3] if len(trozos) > 3 else '0.m3u8')
            if tipo == 'seg':
                n = int(trozos[3]) if len(trozos) > 3 and trozos[3].isdigit() else -1
                if not 0 <= n < len(fuente.recursos):
                    return self._error(h, 404)
                return self._reenviar(h, fuente.recursos[n], fuente.datos['cabeceras'], solo_cabeceras)
            if tipo == 'directo':
                return self._reenviar(h, fuente.datos['url'], fuente.datos['cabeceras'], solo_cabeceras)
            if tipo == 'local':
                return self._archivo(h, fuente.datos['ruta'], solo_cabeceras)
            if tipo == 'remux':
                t = urllib.parse.parse_qs(partes.query).get('t', ['0'])[0]
                return self._remux(h, fuente, max(0.0, float(t) if re.fullmatch(r'\d+(\.\d+)?', t) else 0.0), solo_cabeceras)
            if tipo == 'subs':
                return self._subs(h, fuente)
            if tipo == 'torrent':
                return self._torrent(h, fuente, solo_cabeceras)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            return None
        except Exception:  # noqa: BLE001 - un recurso que falla no debe tumbar el servidor
            try:
                return self._error(h, 502)
            except OSError:
                return None
        return self._error(h, 404)

    @staticmethod
    def _error(h, codigo):
        h.send_response(codigo)
        h.send_header('Content-Length', '0')
        h.send_header('Access-Control-Allow-Origin', '*')
        h.end_headers()

    @staticmethod
    def _pedir(url, cabeceras, rango=None, timeout=20):
        cab = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                             'Chrome/130.0 Safari/537.36', **(cabeceras or {})}
        if rango:
            cab['Range'] = rango
        return urllib.request.urlopen(urllib.request.Request(url, headers=cab), timeout=timeout)

    def _manifiesto(self, h, fuente, id_, nombre):
        n = int(nombre.split('.')[0]) if nombre.split('.')[0].isdigit() else -1
        if not 0 <= n < len(fuente.recursos):
            return self._error(h, 404)
        url = fuente.recursos[n]
        with self._pedir(url, fuente.datos['cabeceras']) as r:
            texto = r.read(8 * 1024 * 1024).decode('utf-8', 'replace')
            final = r.geturl()

        # En una lista maestra, todo lo que se referencia son otras listas; en una de medios, segmentos (y su
        # inicialización EXT-X-MAP o clave EXT-X-KEY). No vale mirar la URL: los segmentos de YouTube llevan
        # "/playlist/index.m3u8/" en la ruta.
        maestra = '#EXT-X-STREAM-INF' in texto or '#EXT-X-MEDIA:' in texto

        def reescribir(uri, es_lista):
            k = fuente.registrar(urllib.parse.urljoin(final, uri.strip()))
            return f'{self.base}/hls/{id_}/{k}.m3u8' if es_lista else f'{self.base}/seg/{id_}/{k}'

        lineas = []
        for linea in texto.splitlines():
            if linea.startswith('#'):
                lista = maestra and linea.startswith(('#EXT-X-MEDIA:', '#EXT-X-I-FRAME-STREAM-INF'))
                linea = URI_ATRIBUTO.sub(lambda m: f'URI="{reescribir(m.group(1), lista)}"', linea)
            elif linea.strip():
                linea = reescribir(linea, maestra)
            lineas.append(linea)
        cuerpo = ('\n'.join(lineas) + '\n').encode('utf-8')
        h.send_response(200)
        h.send_header('Content-Type', 'application/vnd.apple.mpegurl')
        h.send_header('Content-Length', str(len(cuerpo)))
        h.send_header('Access-Control-Allow-Origin', '*')
        h.send_header('Cache-Control', 'no-store')
        h.end_headers()
        h.wfile.write(cuerpo)

    def _reenviar(self, h, url, cabeceras, solo_cabeceras):
        rango = h.headers.get('Range')
        with self._pedir(url, cabeceras, rango) as r:
            h.send_response(r.status)
            for clave in ('Content-Type', 'Content-Length', 'Content-Range', 'Accept-Ranges', 'Last-Modified'):
                if r.headers.get(clave):
                    h.send_header(clave, r.headers[clave])
            if not r.headers.get('Accept-Ranges'):
                h.send_header('Accept-Ranges', 'bytes')
            h.send_header('Access-Control-Allow-Origin', '*')
            if not r.headers.get('Content-Length'):
                # Sin longitud (el origen respondió por trozos): se cierra al acabar para que el reproductor sepa
                # dónde termina; si no, WebView2 esperaría más datos en la conexión abierta
                h.send_header('Connection', 'close')
                h.close_connection = True
            h.end_headers()
            if solo_cabeceras:
                return
            while bloque := r.read(BLOQUE):
                h.wfile.write(bloque)

    @staticmethod
    def _archivo(h, ruta, solo_cabeceras):
        if not os.path.isfile(ruta):
            return Proxy._error(h, 404)
        total = os.path.getsize(ruta)
        inicio, fin = 0, total - 1
        rango = re.fullmatch(r'bytes=(\d*)-(\d*)', h.headers.get('Range') or '')
        if rango and (rango.group(1) or rango.group(2)):
            if rango.group(1):
                inicio = int(rango.group(1))
                fin = min(int(rango.group(2)), total - 1) if rango.group(2) else total - 1
            else:
                inicio = max(0, total - int(rango.group(2)))
            if inicio > fin:
                h.send_response(416)
                h.send_header('Content-Range', f'bytes */{total}')
                h.send_header('Content-Length', '0')
                h.end_headers()
                return
            h.send_response(206)
            h.send_header('Content-Range', f'bytes {inicio}-{fin}/{total}')
        else:
            h.send_response(200)
        h.send_header('Content-Type', TIPOS.get(os.path.splitext(ruta)[1].lower(), 'application/octet-stream'))
        h.send_header('Content-Length', str(fin - inicio + 1))
        h.send_header('Accept-Ranges', 'bytes')
        h.send_header('Access-Control-Allow-Origin', '*')
        h.end_headers()
        if solo_cabeceras:
            return
        with open(ruta, 'rb') as f:
            f.seek(inicio)
            restante = fin - inicio + 1
            while restante > 0 and (bloque := f.read(min(BLOQUE, restante))):
                h.wfile.write(bloque)
                restante -= len(bloque)

    def _remux(self, h, fuente, t, solo_cabeceras):
        ffmpeg = self.ffmpeg() if self.ffmpeg else None
        if not ffmpeg:
            return self._error(h, 503)
        comando = [ffmpeg, '-hide_banner', '-loglevel', 'error', '-nostdin']
        for entrada, cabeceras in fuente.datos['entradas']:
            if entrada.startswith(('http://', 'https://')):
                cab = ''.join(f'{k}: {v}\r\n' for k, v in (cabeceras or {}).items() if k.lower() != 'user-agent')
                ua = (cabeceras or {}).get('User-Agent')
                if ua:
                    comando += ['-user_agent', ua]
                if cab:
                    comando += ['-headers', cab]
                comando += ['-reconnect', '1', '-reconnect_streamed', '1']
            comando += ['-ss', f'{t:.3f}', '-i', entrada]
        if fuente.datos['solo_audio']:
            comando += ['-map', '0:a:0', '-c:a', 'aac', '-b:a', '192k', '-f', 'mp4']
        else:
            comando += ['-map', '0:v:0', '-map', '1:a:0' if len(fuente.datos['entradas']) > 1 else '0:a:0?']
            if fuente.datos['transcodificar']:
                comando += ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '21', '-pix_fmt', 'yuv420p']
            else:
                comando += ['-c:v', 'copy']
            comando += ['-c:a', 'aac', '-b:a', '192k', '-f', 'mp4']
        comando += ['-movflags', 'frag_keyframe+empty_moov+default_base_moof', 'pipe:1']
        h.send_response(200)
        h.send_header('Content-Type', 'video/mp4')
        h.send_header('Access-Control-Allow-Origin', '*')
        h.send_header('Cache-Control', 'no-store')
        h.send_header('Connection', 'close')
        h.end_headers()
        h.close_connection = True
        if solo_cabeceras:
            return
        p = subprocess.Popen(comando, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
                             creationflags=SIN_VENTANA)
        self.procesos.add(p)
        try:
            while bloque := p.stdout.read(BLOQUE):
                h.wfile.write(bloque)
        finally:
            try:
                p.kill()
            except OSError:
                pass
            self.procesos.discard(p)

    def _torrent(self, h, fuente, solo_cabeceras):
        torrents, clave = fuente.datos['torrents'], fuente.datos['clave']
        t = torrents.datos(clave)
        if t is None:
            return self._error(h, 404)
        total = t['tamano']
        inicio, fin = 0, total - 1
        rango = re.fullmatch(r'bytes=(\d*)-(\d*)', h.headers.get('Range') or '')
        if rango and (rango.group(1) or rango.group(2)):
            if rango.group(1):
                inicio = int(rango.group(1))
                fin = min(int(rango.group(2)), total - 1) if rango.group(2) else total - 1
            else:
                inicio = max(0, total - int(rango.group(2)))
            h.send_response(206)
            h.send_header('Content-Range', f'bytes {inicio}-{fin}/{total}')
        else:
            h.send_response(200)
        h.send_header('Content-Type', TIPOS.get(os.path.splitext(t['nombre'])[1].lower(), 'application/octet-stream'))
        h.send_header('Content-Length', str(fin - inicio + 1))
        h.send_header('Accept-Ranges', 'bytes')
        h.send_header('Access-Control-Allow-Origin', '*')
        h.end_headers()
        if solo_cabeceras:
            return
        for trozo in torrents.bloques(clave, inicio, fin):
            h.wfile.write(trozo)

    def _subs(self, h, fuente):
        d = fuente.datos
        if d.get('url'):
            with self._pedir(d['url'], d['cabeceras']) as r:
                texto = r.read(5 * 1024 * 1024).decode('utf-8', 'replace')
        elif d.get('ruta') and os.path.isfile(d['ruta']):
            if d.get('pista') is not None:
                ffmpeg = self.ffmpeg() if self.ffmpeg else None
                if not ffmpeg:
                    return self._error(h, 503)
                r = subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-nostdin', '-i', d['ruta'],
                                    '-map', f"0:s:{int(d['pista'])}", '-f', 'webvtt', 'pipe:1'],
                                   capture_output=True, timeout=60, creationflags=SIN_VENTANA)
                texto = r.stdout.decode('utf-8', 'replace')
            else:
                with open(d['ruta'], 'r', encoding='utf-8', errors='replace') as f:
                    texto = f.read(5 * 1024 * 1024)
        else:
            return self._error(h, 404)
        cuerpo = srt_a_vtt(texto).encode('utf-8')
        h.send_response(200)
        h.send_header('Content-Type', 'text/vtt; charset=utf-8')
        h.send_header('Content-Length', str(len(cuerpo)))
        h.send_header('Access-Control-Allow-Origin', '*')
        h.end_headers()
        h.wfile.write(cuerpo)


def srt_a_vtt(texto):
    """Convierte SRT a WebVTT (si ya es VTT lo deja igual)."""
    texto = texto.lstrip('﻿')
    if texto.lstrip().startswith('WEBVTT'):
        return texto
    cuerpo = re.sub(r'(\d{2}:\d{2}:\d{2}),(\d{3})', r'\1.\2', texto.replace('\r\n', '\n'))
    return 'WEBVTT\n\n' + cuerpo
