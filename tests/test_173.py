"""1.7.3: elegir la pista de audio cuando el video y el audio van por separado (doblajes) o en archivos locales."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jabsdlp import ver  # noqa: E402


def _info():
    return {'formats': [
        {'url': 'https://v/1', 'vcodec': 'avc1.64', 'acodec': 'none', 'protocol': 'https', 'height': 720},
        {'url': 'https://a/pt-lo', 'vcodec': 'none', 'acodec': 'opus', 'protocol': 'https', 'abr': 50, 'language': 'pt'},
        {'url': 'https://a/pt', 'vcodec': 'none', 'acodec': 'mp4a.40.2', 'protocol': 'https', 'abr': 128, 'language': 'pt'},
        {'url': 'https://a/en', 'vcodec': 'none', 'acodec': 'mp4a.40.2', 'protocol': 'https', 'abr': 128,
         'language': 'en', 'language_preference': 10, 'format_note': 'English original'},
        {'url': 'https://a/es', 'vcodec': 'none', 'acodec': 'mp4a.40.2', 'protocol': 'https', 'abr': 128, 'language': 'es'},
    ]}


def test_dash_ofrece_una_pista_por_idioma_con_la_original_primero():
    modo, datos = ver.elegir_fuente(_info(), 'https://example.com/v')
    assert modo == 'remux'
    assert datos['entradas'][1][0] == 'https://a/en'
    urls = [u for u, _ in datos['audios']]
    assert urls[0] == 'https://a/en' and len(urls) == 3 and 'https://a/pt' in urls and 'https://a/pt-lo' not in urls
    assert datos['nombres_audio'][0]['original'] is True
    assert [n['idioma'] for n in datos['nombres_audio']][0] == 'en'


def test_una_sola_pista_no_ofrece_selector():
    info = {'formats': [f for f in _info()['formats'] if f.get('language') in (None, 'en')]}
    _, datos = ver.elegir_fuente(info, 'https://example.com/v')
    assert 'audios' not in datos


def test_subtitulos_incluyen_todas_las_traducciones_automaticas():
    vtt = lambda nombre: [{'ext': 'vtt', 'url': 'https://s/' + nombre, 'name': nombre}]
    info = {'subtitles': {'de': vtt('German'), 'en': vtt('English')},
            'automatic_captions': {'en-orig': vtt('English (Original)'), 'en': vtt('English'), 'fr': vtt('French'),
                                   'es': vtt('Spanish'), 'zu': vtt('Zulu'), 'ab': vtt('Abkhazian')}}
    nombres = [s['nombre'] for s in ver._subtitulos_de(info, _ProxyFalso())]
    # primero los del autor (en antes que de por ser preferido), luego las traducciones: es primero, el resto por nombre
    assert nombres == ['English', 'German', 'Spanish (traducción automática)', 'Abkhazian (traducción automática)',
                       'French (traducción automática)', 'Zulu (traducción automática)']
    sin_manuales = {'automatic_captions': info['automatic_captions']}
    assert [s['nombre'] for s in ver._subtitulos_de(sin_manuales, _ProxyFalso())][0] == 'English (Original) (automáticos)'


class _ProxyFalso:
    def local(self, ruta):
        return 'local:' + ruta

    def remux(self, entradas, transcodificar=False, solo_audio=False, audios=None):
        return 'remux:' + entradas[0][0]

    def subtitulos(self, **kw):
        return 'subs'


def test_archivo_local_con_dos_audios_se_une_al_vuelo(tmp_path, monkeypatch):
    archivo = tmp_path / 'peli.mp4'
    archivo.write_bytes(b'x')
    monkeypatch.setattr(ver, 'sondear', lambda ruta, ffprobe: ('h264', 'aac', 30.0, [], [(0, 'spa', 'Español'), (1, 'eng', None)]))
    datos = ver.resolver_local(str(archivo), _ProxyFalso(), 'ffprobe')
    assert datos['modo'] == 'remux'
    assert [a['nombre'] for a in datos['audios']] == ['Español', 'eng']
    monkeypatch.setattr(ver, 'sondear', lambda ruta, ffprobe: ('h264', 'aac', 30.0, [], [(0, 'spa', None)]))
    datos = ver.resolver_local(str(archivo), _ProxyFalso(), 'ffprobe')
    assert datos['modo'] == 'directo' and 'audios' not in datos


def test_perfiles_se_validan(tmp_path, monkeypatch):
    monkeypatch.setenv('APPDATA', str(tmp_path))
    from jabsdlp.ajustes import Ajustes
    a = Ajustes()
    r = a.actualizar({'perfiles': [{'id': 'p1', 'nombre': ' Solo audio ', 'prefs': {'tipo': 'audio', 'formato_audio': 'mp3', 'raro': 1}},
                                   {'id': 'mal id!', 'nombre': 'x', 'prefs': {}}, {'id': 'p1', 'nombre': 'repetido'}]})
    assert [p['nombre'] for p in r['perfiles']] == ['Solo audio']
    prefs = r['perfiles'][0]['prefs']
    assert prefs['tipo'] == 'audio' and prefs['formato_audio'] == 'mp3' and 'raro' not in prefs


def test_biblioteca_con_subcarpetas(tmp_path):
    from jabsdlp import biblioteca
    (tmp_path / 'a' / 'b').mkdir(parents=True)
    (tmp_path / '.oculta').mkdir()
    for ruta in ('x.mp4', 'a/y.mkv', 'a/b/z.mp3', '.oculta/w.mp4', 'a/nota.txt'):
        (tmp_path / ruta).write_bytes(b'x')
    normal = biblioteca.listar(str(tmp_path))
    assert [c['nombre'] for c in normal['carpetas']] == ['a'] and [a['nombre'] for a in normal['archivos']] == ['x.mp4']
    todo = biblioteca.listar(str(tmp_path), recursivo=True)
    hallados = sorted((a['carpeta'].replace(os.sep, '/'), a['nombre']) for a in todo['archivos'])
    assert hallados == [('', 'x.mp4'), ('a', 'y.mkv'), ('a/b', 'z.mp3')]
