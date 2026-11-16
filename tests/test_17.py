"""1.7.0: proxy local de la pestaña Ver, elección de la fuente y progreso en colecciones."""
import functools
import hashlib
import os
import sys
import threading
import urllib.error
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from jabsdlp import ver  # noqa: E402
from jabsdlp.colecciones import Colecciones  # noqa: E402
from jabsdlp.proxy import Proxy, srt_a_vtt  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def proxy():
    p = Proxy(None)
    yield p
    p.cerrar()


def leer(url, cabeceras=None):
    with urllib.request.urlopen(urllib.request.Request(url, headers=cabeceras or {}), timeout=10) as r:
        return r.status, dict(r.headers), r.read()


def test_token_incorrecto_da_404(proxy, tmp_path):
    archivo = tmp_path / 'a.mp4'
    archivo.write_bytes(b'0123456789')
    url = proxy.local(str(archivo))
    with pytest.raises(urllib.error.HTTPError) as e:
        leer(url.replace(proxy.token, 'x' * len(proxy.token)))
    assert e.value.code == 404
    with pytest.raises(urllib.error.HTTPError):
        leer(url.rsplit('/', 1)[0] + '/noexiste')


def test_archivo_local_con_range(proxy, tmp_path):
    archivo = tmp_path / 'video.mp4'
    archivo.write_bytes(bytes(range(256)) * 4)
    url = proxy.local(str(archivo))
    estado, cab, cuerpo = leer(url, {'Range': 'bytes=10-19'})
    assert estado == 206 and cuerpo == bytes(range(10, 20)) and cab['Content-Range'] == 'bytes 10-19/1024'
    estado, cab, cuerpo = leer(url)
    assert estado == 200 and len(cuerpo) == 1024 and cab['Content-Type'] == 'video/mp4'


def test_hls_reescribe_maestra_y_medios(proxy, tmp_path):
    # servidor de prueba con una maestra, una variante (con EXT-X-MAP y segmentos) y una pista de audio
    (tmp_path / 'master.m3u8').write_text('#EXTM3U\n#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="a",URI="audio/index.m3u8"\n'
                                          '#EXT-X-STREAM-INF:BANDWIDTH=1000,AUDIO="a"\nv/index.m3u8\n', encoding='utf-8')
    (tmp_path / 'v').mkdir()
    (tmp_path / 'audio').mkdir()
    # los segmentos llevan "index.m3u8" en la ruta, como los de YouTube: deben seguir siendo segmentos
    (tmp_path / 'v' / 'index.m3u8').write_text('#EXTM3U\n#EXT-X-MAP:URI="init.mp4"\n#EXTINF:4,\nindex.m3u8.seg0.ts\n',
                                               encoding='utf-8')
    (tmp_path / 'v' / 'index.m3u8.seg0.ts').write_bytes(b'G' * 100)
    (tmp_path / 'v' / 'init.mp4').write_bytes(b'init')
    (tmp_path / 'audio' / 'index.m3u8').write_text('#EXTM3U\n#EXTINF:4,\na0.aac\n', encoding='utf-8')
    servidor = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(SimpleHTTPRequestHandler, directory=str(tmp_path)))
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    try:
        maestra = leer(proxy.hls(f'http://127.0.0.1:{servidor.server_address[1]}/master.m3u8', {'Referer': 'https://x.com/'}))[2].decode()
        assert '127.0.0.1:%d' % servidor.server_address[1] not in maestra and proxy.token in maestra
        variante_url = [l for l in maestra.splitlines() if l.startswith('http')][0]
        assert variante_url.endswith('.m3u8')
        assert '/hls/' in maestra.split('URI="')[1]          # la pista de audio también es una lista
        variante = leer(variante_url)[2].decode()
        seg = [l for l in variante.splitlines() if l.startswith('http')][0]
        assert '/seg/' in seg and '/seg/' in variante.split('URI="')[1].split('"')[0]
        assert leer(seg)[2] == b'G' * 100
    finally:
        servidor.shutdown()


def test_olvidar_libera_las_fuentes(proxy, tmp_path):
    archivo = tmp_path / 'a.mp3'
    archivo.write_bytes(b'x')
    url = proxy.local(str(archivo))
    proxy.olvidar()
    with pytest.raises(urllib.error.HTTPError):
        leer(url)


def test_srt_a_vtt():
    assert srt_a_vtt('1\n00:00:01,500 --> 00:00:02,000\nHola\n').startswith('WEBVTT\n\n1\n00:00:01.500 --> 00:00:02.000')
    assert srt_a_vtt('WEBVTT\n\nx') == 'WEBVTT\n\nx'


# ---------- elección de la fuente ----------
def test_prefiere_hls_si_hay_manifiesto():
    info = {'formats': [{'protocol': 'm3u8_native', 'manifest_url': 'https://m/master.m3u8', 'url': 'https://m/v.m3u8',
                         'vcodec': 'avc1', 'http_headers': {'User-Agent': 'UA'}},
                        {'protocol': 'https', 'url': 'https://v.mp4', 'vcodec': 'avc1.4d', 'acodec': 'mp4a', 'ext': 'mp4'}]}
    modo, datos = ver.elegir_fuente(info, 'https://youtube.com/watch?v=x')
    assert modo == 'hls' and datos['url'] == 'https://m/master.m3u8' and datos['cabeceras']['User-Agent'] == 'UA'


def test_progresivo_y_remux():
    progresivo = {'formats': [{'protocol': 'https', 'url': 'https://a.mp4', 'vcodec': 'avc1', 'acodec': 'mp4a', 'ext': 'mp4', 'height': 720}]}
    assert ver.elegir_fuente(progresivo, 'u')[0] == 'directo'
    separado = {'formats': [{'protocol': 'https', 'url': 'https://v', 'vcodec': 'vp9', 'acodec': 'none', 'height': 1080},
                            {'protocol': 'https', 'url': 'https://v2', 'vcodec': 'avc1', 'acodec': 'none', 'height': 1080},
                            {'protocol': 'https', 'url': 'https://a', 'vcodec': 'none', 'acodec': 'opus', 'abr': 160}]}
    modo, datos = ver.elegir_fuente(separado, 'u')
    assert modo == 'remux' and datos['entradas'][0][0] == 'https://v2' and datos['entradas'][1][0] == 'https://a'


def test_hevc_local_se_transcodifica(proxy, tmp_path, monkeypatch):
    archivo = tmp_path / 'x.mkv'
    archivo.write_bytes(b'x')
    monkeypatch.setattr(ver, 'sondear', lambda ruta, ffprobe: ('hevc', 'aac', 10.0, [], []))
    d = ver.resolver_local(str(archivo), proxy, 'ffprobe')
    assert d['modo'] == 'remux' and proxy.fuentes[d['src'].rsplit('/', 1)[1]].datos['transcodificar'] is True
    monkeypatch.setattr(ver, 'sondear', lambda ruta, ffprobe: ('h264', 'aac', 10.0, [], []))
    (tmp_path / 'y.mp4').write_bytes(b'x')
    assert ver.resolver_local(str(tmp_path / 'y.mp4'), proxy, 'ffprobe')['modo'] == 'directo'


def test_vistos_sin_tokens(tmp_path, monkeypatch):
    monkeypatch.setenv('APPDATA', str(tmp_path))
    ver.anotar_visto({'origen': 'https://cdn.x.com/v.m3u8?token=SECRETO', 'titulo': 'a'})
    ver.anotar_visto({'origen': 'https://youtu.be/a', 'titulo': 'b', 'miniatura': 'http://inseguro/x.jpg'})
    vistos = ver.leer_vistos()
    assert [v['titulo'] for v in vistos] == ['b'] and vistos[0]['miniatura'] is None


# ---------- progreso en colecciones ----------
def test_progreso_y_visto(tmp_path):
    c = Colecciones(str(tmp_path / 'c.json'))
    id_ = c.crear('Lista', [{'url': 'https://youtu.be/a'}])
    c.progreso(id_, {'url': 'https://youtu.be/a'}, 123.4)
    assert c.obtener(id_)['items'][0]['posicion'] == 123.4
    c.progreso(id_, {'url': 'https://youtu.be/a'}, 0, visto=True)
    item = c.obtener(id_)['items'][0]
    assert item['visto'] is True and 'posicion' not in item


def test_hls_js_incluido_es_el_verificado():
    with open(os.path.join(RAIZ, 'ui', 'vendor', 'hls.min.js'), 'rb') as f:
        assert hashlib.sha256(f.read()).hexdigest() == 'cfc70cc9e9fc63d071919e087670abc760c8fd1bc889b88588026e4d22193bbe'
