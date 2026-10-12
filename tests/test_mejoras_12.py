"""Pruebas de las mejoras de la 1.2.0."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from jabsdlp import formatos, notificar, sponsor  # noqa: E402
from jabsdlp.ajustes import PREFS_POR_DEFECTO, Ajustes  # noqa: E402
from jabsdlp.api import Api, _segundos  # noqa: E402
from jabsdlp.argumentos import ArgumentosInvalidos, interpretar  # noqa: E402
from jabsdlp.trabajo import Trabajo, plantilla_salida  # noqa: E402
from jabsdlp.utilidades import clasificar_error  # noqa: E402
from jabsdlp.velocidad import Cubeta, mb_a_bytes  # noqa: E402


def audio(fid, lengua, abr, preferencia=-1, acodec='opus'):
    return {'format_id': fid, 'ext': 'webm', 'vcodec': 'none', 'acodec': acodec, 'abr': abr, 'tbr': abr,
            'filesize': abr * 10000, 'protocol': 'https', 'language': lengua, 'language_preference': preferencia}


INFO = {'duration': 100, 'formats': [
    audio('251-0', 'en-US', 130, 10), audio('251-1', 'es', 128), audio('251-2', 'pt', 129), audio('250-1', 'es', 70),
    {'format_id': '399', 'ext': 'mp4', 'vcodec': 'av01.0.08M.08', 'acodec': 'none', 'height': 1080, 'fps': 30,
     'tbr': 2000, 'filesize': 25_000_000, 'protocol': 'https'},
]}


def prefs(**c):
    return {**PREFS_POR_DEFECTO, **c}


# ---------- A. errores temporales ----------
@pytest.mark.parametrize('mensaje,temporal', [
    ('HTTP Error 503: Service Unavailable', True), ('HTTP Error 429: Too Many Requests', True),
    ('<urlopen error [Errno 11001] getaddrinfo failed>', True), ('Read timed out.', True),
    ('[youtube] x: Private video', False), ('[youtube] x: This video is unavailable', False),
    ('Unsupported URL: https://x', False), ('algo raro que no conocemos', False),
])
def test_errores_temporales(mensaje, temporal):
    assert clasificar_error(mensaje)[2] is temporal


# ---------- B. idioma del audio ----------
def test_idioma_audio_elige_la_pista():
    c = formatos.calcular(INFO, prefs(idioma_audio='es'))
    assert c['audio_elegido'] == '251-1' and c['recomendado']['spec'] == '399+251-1' and c['aviso_idioma'] is None


def test_idioma_original_por_defecto():
    assert formatos.calcular(INFO, prefs())['audio_elegido'] == '251-0'


def test_idioma_inexistente_avisa_y_usa_original():
    c = formatos.calcular(INFO, prefs(idioma_audio='ja'))
    assert c['audio_elegido'] == '251-0' and c['aviso_idioma']


def test_idioma_con_ahorro_usa_pista_media_del_idioma():
    assert formatos.calcular(INFO, prefs(idioma_audio='es', criterio='ahorro'))['audio_elegido'] == '250-1'


def test_selector_playlist_con_idioma():
    fmt, _ = formatos.selector_por_preferencias(prefs(idioma_audio='es'))
    assert fmt.split('/')[0].startswith('bv+ba[language^=es]')
    fmt, _ = formatos.selector_por_preferencias(prefs(tipo='audio', idioma_audio='en'))
    assert fmt.startswith('ba[language^=en]')
    fmt, _ = formatos.selector_por_preferencias(prefs(idioma_audio="es]+[x"))  # código raro: se ignora
    assert 'language' not in fmt


# ---------- 4. límite de velocidad ----------
def test_cubeta_limita_el_total():
    cubeta = Cubeta(lambda: 1_000_000)  # 1 MB/s
    inicio = time.monotonic()
    for _ in range(4):
        cubeta.consumir(500_000)
    assert time.monotonic() - inicio >= 1.4  # 2 MB a 1 MB/s con 0,5 s de ráfaga


def test_cubeta_sin_limite_no_espera():
    assert Cubeta(lambda: 0).consumir(10_000_000) == 0.0


def test_bytes_nuevos_por_archivo():
    c = Cubeta(lambda: 0)
    assert c.bytes_nuevos('a', 100) == 100 and c.bytes_nuevos('a', 250) == 150 and c.bytes_nuevos('b', 40) == 40
    assert mb_a_bytes(5) == 5 * 1024 * 1024 and mb_a_bytes('x') == 0


# ---------- 5. recorte ----------
def test_segundos():
    assert _segundos('1:20') == 80 and _segundos('01:02:03') == 3723 and _segundos('45') == 45
    assert _segundos('a:b') is None and _segundos('-1') is None


def test_validar_recorte():
    assert Api._validar_recorte(['1:20', '3:45'], 600) == [80, 225]
    assert Api._validar_recorte(['3:45', '1:20'], 600) is None
    assert Api._validar_recorte(['0:10', '99:00'], 60) == [10, 60]


# ---------- 8. numeración y sufijo de recorte ----------
def test_plantilla_salida():
    t = Trabajo('u', {}, indice=3, total_grupo=120, recorte=[80, 225])
    assert plantilla_salida('%(title)s.%(ext)s', t, True) == '003 - %(title)s [1m20s-3m45s].%(ext)s'
    assert plantilla_salida('%(uploader)s/%(title)s.%(ext)s', Trabajo('u', {}, indice=7, total_grupo=9), True) == \
        '%(uploader)s/07 - %(title)s.%(ext)s'
    assert plantilla_salida('%(title)s.%(ext)s', Trabajo('u', {}, indice=7), False) == '%(title)s.%(ext)s'


# ---------- 1. retomar la cola ----------
def test_trabajo_pendiente_se_restaura_en_cola():
    t = Trabajo('https://x', prefs(), titulo='T', grupo_id='g', indice=2, total_grupo=5, recorte=[1, 9],
                quitar_anuncios=True)
    t.estado = 'descargando'
    r = Trabajo.pendiente_desde_dict(t.a_dict())
    assert r.estado == 'en_cola' and r.id == t.id and r.indice == 2 and r.recorte == [1, 9] and r.quitar_anuncios


# ---------- E. comando personalizado ----------
def test_argumentos_validos_y_bloqueados():
    extra, pps = interpretar('--sleep-requests 1 --embed-chapters')
    assert extra == {'sleep_interval_requests': 1.0} and pps[0]['key'] == 'FFmpegMetadata'
    for malo in ('--exec calc', '--exec=calc', '--plugin-dirs C:/x', '-o C:/x', '--downloader curl', 'https://youtu.be/x',
                 '--opcion-inventada'):
        with pytest.raises(ArgumentosInvalidos):
            interpretar(malo)


# ---------- 3. notificaciones seguras ----------
def test_xml_de_notificacion_escapa_todo():
    xml = notificar.construir_xml("$(calc) '@ <b>&", '`whoami` "x"\n', None, None)
    assert '$(calc)' in xml and '<b>' not in xml and "'" not in xml and '\n' not in xml and '&amp;' in xml


# ---------- C. SponsorBlock ----------
def test_duracion_total_une_solapes():
    segmentos = [{'inicio': 10, 'fin': 20}, {'inicio': 15, 'fin': 30}, {'inicio': 50, 'fin': 55}]
    assert sponsor.duracion_total(segmentos) == 25
    assert sponsor.categorias_validas('sponsor,raro,intro') == ['sponsor', 'intro']


# ---------- ajustes nuevos ----------
def test_ajustes_nuevos_validados(tmp_path):
    a = Ajustes(os.path.join(tmp_path, 's.json'))
    a.actualizar({'limite_velocidad': '7.5', 'reintentos': 50, 'motor': 'curl', 'tema': 'claro',
                  'aria2_ruta': 'C:/Windows/notepad.exe', 'prefs': {'idioma_audio': 'pt-BR', 'idioma_subs': 'es,en,$(x)',
                                                                    'sponsor_cats': 'sponsor,malo'}})
    assert a.get('limite_velocidad') == 7.5 and a.get('reintentos') == 10 and a.get('motor') == 'ytdlp'
    assert a.get('tema') == 'claro' and a.get('aria2_ruta') == ''
    p = a.get('prefs')
    assert p['idioma_audio'] == 'pt-BR' and p['idioma_subs'] == 'es,en' and p['sponsor_cats'] == 'sponsor'


# ---------- seguridad: aria2, torrents, archivos peligrosos ----------
def test_aria2_solo_descargas_directas_y_sin_torrent():
    from jabsdlp import aria2
    args = aria2.argumentos(1000)
    assert '--follow-torrent=false' in args and '--follow-metalink=false' in args
    assert aria2.ytdlp_seguro_para_aria2()  # el yt-dlp incluido ya corrige CVE-2026-50574
    t = aria2.argumentos_torrent('C:/x', 0, 15)
    assert '--seed-time=0' in t and '--no-conf' in t and '--max-overall-upload-limit=15K' in t and '--enable-rpc=false' in t


def test_torrents_y_extensiones():
    from jabsdlp.utilidades import es_medio, es_torrent, extension_peligrosa, nombre_torrent
    assert es_torrent('magnet:?xt=urn:btih:abc&dn=Big+Buck+Bunny') and es_torrent('C:/a/b.torrent')
    assert not es_torrent('https://youtube.com/watch?v=x')
    assert nombre_torrent('magnet:?xt=urn:btih:abc&dn=Big+Buck+Bunny') == 'Big Buck Bunny'
    assert extension_peligrosa('https://x.com/setup.EXE?a=1') and not extension_peligrosa('https://x.com/v.mp4')
    assert es_medio('a.MKV') and not es_medio('a.bat')


def test_riesgos_de_la_fuente():
    from jabsdlp.analizador import riesgos
    assert riesgos('http://x.com/v', {'extractor_key': 'Generic', 'ext': 'mp4'}) == ['http', 'generico']
    assert riesgos('https://x.com/a.exe', {'extractor_key': 'Generic', 'ext': 'exe'}) == ['generico', 'ejecutable']
    assert riesgos('https://www.youtube.com/watch?v=x', {'extractor_key': 'Youtube', 'ext': 'mp4'}) == []


def test_avisos_ocultos_validados(tmp_path):
    a = Ajustes(os.path.join(tmp_path, 's.json'))
    a.actualizar({'avisos_ocultos': ['torrent', 'inventado', 'http']})
    assert a.get('avisos_ocultos') == ['http', 'torrent']


def test_filtros_de_dialogo_validos_para_pywebview():
    import re
    from webview.util import parse_file_type
    texto = open(os.path.join(os.path.dirname(__file__), '..', 'jabsdlp', 'api.py'), encoding='utf-8').read()
    filtros = re.findall(r"'([^']+ \(\*[^']*\))'", texto)
    assert len(filtros) >= 6
    for f in filtros:
        parse_file_type(f)   # lanza ValueError si el formato no es válido


def test_trabajo_guarda_inicio_en_historial():
    from jabsdlp.trabajo import Trabajo
    t = Trabajo('https://example.com/v', {'tipo': 'video'})
    t.estado, t.inicio, t.terminado = 'completado', 100.0, 165.0
    copia = Trabajo.desde_dict(t.a_dict())
    assert (copia.inicio, copia.terminado) == (100.0, 165.0)
    t.reiniciar()
    assert t.inicio is None


def test_desinstalar_aria2_solo_borra_su_carpeta(tmp_path, monkeypatch):
    from jabsdlp import aria2
    monkeypatch.setattr(aria2, 'carpeta_local', lambda: str(tmp_path))
    (tmp_path / 'aria2').mkdir()
    (tmp_path / 'aria2' / 'aria2c.exe').write_bytes(b'x')
    (tmp_path / 'otro.txt').write_text('no tocar')
    assert aria2.instalado_por_la_app()
    aria2.desinstalar()
    assert not aria2.instalado_por_la_app()
    assert (tmp_path / 'otro.txt').exists()
    aria2.desinstalar()   # sin carpeta no falla
