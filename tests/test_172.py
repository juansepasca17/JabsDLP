"""1.7.2: subtítulos automáticos de YouTube limpios, audio original, stack con torrents y enlaces directos."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jabsdlp.proxy import limpiar_vtt  # noqa: E402
from jabsdlp.ver import elegir_fuente, idioma_original  # noqa: E402

VTT_YOUTUBE = """WEBVTT
Kind: captions
Language: es

00:00:00.160 --> 00:00:02.869 align:start position:0%

hola<00:00:00.480><c> a</c><00:00:00.800><c> todos</c>

00:00:02.869 --> 00:00:02.879 align:start position:0%
hola a todos


00:00:02.879 --> 00:00:05.200 align:start position:0%
hola a todos
bienvenidos<00:00:03.200><c> al</c><00:00:03.600><c> canal</c>

00:00:05.200 --> 00:00:05.210 align:start position:0%
bienvenidos al canal


00:00:05.210 --> 00:00:07.000 align:start position:0%
bienvenidos al canal

"""


def _cues(vtt):
    bloques = [b for b in vtt.split('\n\n') if '-->' in b]
    return [(b.strip().split('\n')[0], [l for l in b.strip().split('\n')[1:] if l]) for b in bloques]


def test_limpia_subtitulos_automaticos():
    limpio = limpiar_vtt(VTT_YOUTUBE)
    assert '<c>' not in limpio and '<00:' not in limpio
    cues = _cues(limpio)
    # sin cues de 10 ms y sin repetidos seguidos
    assert len(cues) == 3
    assert cues[0][1] == ['hola a todos']
    assert cues[1][1] == ['hola a todos', 'bienvenidos al canal']
    assert cues[2][1] == ['bienvenidos al canal']
    # ninguno se solapa con el siguiente
    tiempos = [c[0].split(' --> ') for c in cues]
    for (_, fin), (inicio, _) in zip(tiempos, tiempos[1:]):
        assert fin <= inicio


def test_subtitulos_normales_no_se_tocan():
    normal = 'WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nHola\n'
    assert limpiar_vtt(normal) == normal


def test_idioma_original():
    info = {'formats': [
        {'format_id': '1', 'acodec': 'mp4a', 'language': 'pt-BR', 'language_preference': -1},
        {'format_id': '2', 'acodec': 'mp4a', 'language': 'en', 'language_preference': 10},
        {'format_id': '3', 'acodec': 'mp4a', 'language': 'es', 'language_preference': 5},
    ]}
    assert idioma_original(info) == 'en'
    assert idioma_original({'formats': [{'acodec': 'mp4a', 'language': 'es', 'language_preference': 5}]}) is None


def test_remux_prefiere_audio_original():
    info = {'formats': [
        {'url': 'https://v/1', 'vcodec': 'avc1.64', 'acodec': 'none', 'protocol': 'https', 'height': 720},
        {'url': 'https://a/pt', 'vcodec': 'none', 'acodec': 'mp4a.40.2', 'protocol': 'https', 'abr': 160,
         'language': 'pt', 'language_preference': 5, 'format_note': 'Portuguese (default)'},
        {'url': 'https://a/en', 'vcodec': 'none', 'acodec': 'mp4a.40.2', 'protocol': 'https', 'abr': 128,
         'language': 'en', 'language_preference': 10, 'format_note': 'English original'},
    ]}
    modo, datos = elegir_fuente(info, 'https://example.com/v')
    assert modo == 'remux'
    assert datos['entradas'][1][0] == 'https://a/en'


def _entorno(tmp_path, monkeypatch):
    """Carpetas de prueba y sin la actualización automática de yt-dlp (que corre en segundo plano)."""
    import json
    monkeypatch.setenv('APPDATA', str(tmp_path))
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path / 'local'))
    (tmp_path / 'JabsDLP').mkdir(exist_ok=True)
    (tmp_path / 'JabsDLP' / 'settings.json').write_text(json.dumps({'ytdlp_auto': False}), encoding='utf-8')


def test_stack_acepta_torrents_y_enlaces_directos(tmp_path, monkeypatch):
    _entorno(tmp_path, monkeypatch)
    from jabsdlp import aria2
    from jabsdlp.api import Api
    api = Api()
    agregados = []
    monkeypatch.setattr(api._gestor, 'agregar', lambda trabajos: agregados.extend(trabajos))
    monkeypatch.setattr(aria2, 'ruta', lambda ajustes=None: None)
    items = [{'url': 'magnet:?xt=urn:btih:' + 'a' * 40, 'titulo': 'peli'},
             {'url': 'https://cdn.example.com/video/master.m3u8', 'titulo': 'Clase 1'},
             {'url': 'https://www.youtube.com/watch?v=aqz-KE-bpKQ', 'titulo': 'Video'}]
    # sin aria2 el magnet da un error claro y no se añade nada
    r = api.descargar({'tipo': 'stack', 'nombre': 'Prueba', 'prefs': {}, 'items': items})
    assert not r['ok'] and 'aria2' in r['error'] and not agregados
    monkeypatch.setattr(aria2, 'ruta', lambda ajustes=None: 'aria2c.exe')
    r = api.descargar({'tipo': 'stack', 'nombre': 'Prueba', 'prefs': {}, 'items': items})
    assert r['ok'] and r['agregados'] == 3
    tipos = sorted(t.prefs.get('tipo') or 'video' for t in agregados)
    assert tipos == ['manifiesto', 'torrent', 'video']
    api.cerrar()


def test_ver_con_log_completo_devuelve_detalle(tmp_path, monkeypatch):
    _entorno(tmp_path, monkeypatch)
    from jabsdlp import ver as ver_mod
    from jabsdlp.api import Api
    api = Api()

    def falla(*a, **k):
        raise RuntimeError('fallo de prueba https://x.com/v?token=SECRETO123')
    monkeypatch.setattr(ver_mod, 'resolver_enlace', falla)
    r = api.ver('https://example.com/video')
    assert not r['ok'] and not r.get('detalle')
    api.guardar_ajustes({'log_completo': True})
    r = api.ver('https://example.com/video')
    assert not r['ok'] and 'RuntimeError' in r['detalle'] and 'SECRETO123' not in r['detalle']
    api.cerrar()
