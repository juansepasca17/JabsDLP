"""1.5.0: enlaces directos .m3u8/.mpd, Referer, filtro del comando personalizado, tokens ocultos y plantillas."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from jabsdlp.ajustes import Ajustes, validar_plantillas  # noqa: E402
from jabsdlp.analizador import _resumen_manifiesto  # noqa: E402
from jabsdlp.argumentos import ArgumentosInvalidos, interpretar  # noqa: E402
from jabsdlp.trabajo import Registro, Trabajo, nombre_libre  # noqa: E402
from jabsdlp.utilidades import es_manifiesto, nombre_manifiesto, ocultar_tokens, referer_desde, tiene_tokens  # noqa: E402

PLATZI = ('https://mediastream.platzi.com/video/h/abc/index-v1-a1.m3u8?cP=SECRETO&pid=P1&sid=S1&uid=U1&aid=A1'
          '&fallback=none&es=mediastream.platzi.com&proto=https')


# ---------- detección ----------
@pytest.mark.parametrize('url, esperado', [
    (PLATZI, 'm3u8'),
    ('https://cdn.x.com/a/MANIFEST.MPD?token=1', 'mpd'),
    ('https://cdn.x.com/a/video.m3u8#t=10', 'm3u8'),
    ('https://cdn.x.com/a/video.M3U8', 'm3u8'),
    ('https://www.youtube.com/watch?v=x&f=.m3u8', None),     # la extensión está en la query, no en la ruta
    ('https://cdn.x.com/m3u8/video.mp4', None),
    ('magnet:?xt=urn:btih:x.m3u8', None),
    ('', None),
])
def test_deteccion_de_manifiesto(url, esperado):
    assert es_manifiesto(url) == esperado


# ---------- Referer ----------
@pytest.mark.parametrize('url, esperado', [
    (PLATZI, 'https://platzi.com/'),
    ('https://cdn.algo.com.co/v/x.m3u8', 'https://algo.com.co/'),
    ('https://a.b.cdn.algo.com.co/v/x.m3u8', 'https://algo.com.co/'),
    ('https://media.bbc.co.uk/x.mpd', 'https://bbc.co.uk/'),
    ('https://platzi.com/x.m3u8', 'https://platzi.com/'),
    ('https://192.168.1.5:8080/x.m3u8', 'https://192.168.1.5/'),
])
def test_referer_desde_el_dominio(url, esperado):
    assert referer_desde(url) == esperado


def test_nombre_del_manifiesto():
    assert nombre_manifiesto(PLATZI) == 'index-v1-a1'
    assert nombre_manifiesto('https://x.com/') == 'video'
    assert nombre_manifiesto('https://x.com/a%3Cb%3E.m3u8') == 'a_b_'


def test_nombre_libre_no_pisa_archivos(tmp_path):
    assert nombre_libre(str(tmp_path), 'clase') == 'clase'
    (tmp_path / 'clase.mp4').write_bytes(b'')
    (tmp_path / 'clase-2.mkv').write_bytes(b'')
    assert nombre_libre(str(tmp_path), 'clase') == 'clase-3'


# ---------- tokens ----------
def test_tokens_ocultos_en_el_log():
    linea = f'[debug] Invoking hlsnative downloader on "{PLATZI}"'
    oculto = ocultar_tokens(linea)
    for secreto in ('SECRETO', 'P1', 'S1', 'U1', 'A1'):
        assert f'={secreto}' not in oculto
    assert 'cP=***' in oculto and 'fallback=none' in oculto and 'proto=https' in oculto
    assert ocultar_tokens('https://s3/x?X-Amz-Signature=abc&Expires=1') == 'https://s3/x?X-Amz-Signature=***&Expires=***'
    assert tiene_tokens(PLATZI) and not tiene_tokens('https://x.com/a.m3u8?fallback=none')


def test_registro_y_url_del_trabajo_sin_tokens():
    t = Trabajo(PLATZI, {'tipo': 'manifiesto', 'referer': 'https://platzi.com/', 'nombre': 'x'})
    r = Registro(t, completo=True)
    r.debug(f'[debug] GET {PLATZI}')
    r.info(f'[hlsnative] Downloading m3u8 manifest {PLATZI}')
    assert not any('SECRETO' in l for l in t.registro)
    assert 'SECRETO' not in t.a_dict()['url'] and t.url == PLATZI   # en memoria sigue el enlace real


def test_registro_corto_no_guarda_debug():
    t = Trabajo('https://youtu.be/x', {'tipo': 'video'})
    Registro(t).debug('[debug] algo')
    assert t.registro == []


# ---------- comando personalizado ----------
@pytest.mark.parametrize('texto', [
    '--referer https://platzi.com/', '--add-header "Referer:https://platzi.com/"', '--add-header=Referer:https://x.com/',
    '-f b', '--no-mtime -S "ext"', '--embed-chapters --sponsorblock-remove sponsor', '--impersonate chrome',
])
def test_comando_permitido(texto):
    interpretar(texto)


@pytest.mark.parametrize('texto, opcion', [
    ('--exec calc', '--exec'), ('--exec=calc', '--exec'), ('--use-postprocessor X', '--use-postprocessor'),
    ('--external-downloader curl', '--external-downloader'), ('--plugin-dirs C:/x', '--plugin-dirs'),
    ('--config-locations a.conf', '--config-locations'), ('-o C:/x', '-o'), ('--ppa "ffmpeg:-i x"', '--ppa'),
])
def test_comando_bloqueado_dice_cual_y_por_que(texto, opcion):
    with pytest.raises(ArgumentosInvalidos) as e:
        interpretar(texto)
    assert str(e.value).startswith(f'Se bloqueó {opcion}:')


def test_comando_fuera_de_la_lista_y_comilla_sin_cerrar():
    with pytest.raises(ArgumentosInvalidos, match='no está en la lista de opciones permitidas'):
        interpretar('--list-formats')
    with pytest.raises(ArgumentosInvalidos, match=r'Comilla " sin cerrar en: "https://platzi\.com/'):
        interpretar('--referer "https://platzi.com/ -f b')


# ---------- resumen del manifiesto ----------
def test_resumen_hls_con_cifrado():
    texto = ('#EXTM3U\n#EXT-X-KEY:METHOD=AES-128,URI="k"\n#EXTINF:6.0,\na.ts\n#EXTINF:4.5,\nb.ts\n#EXT-X-ENDLIST\n')
    assert _resumen_manifiesto(texto, 'm3u8') == {'fragmentos': 2, 'suma': 10.5, 'cifrado': 'aes'}
    assert _resumen_manifiesto('#EXTM3U\n#EXTINF:2,\na.ts\n', 'm3u8')['cifrado'] is None


def test_resumen_dash():
    texto = '<MPD><ContentProtection/><SegmentTimeline><S t="0" d="2" r="9"/><S d="1"/></SegmentTimeline></MPD>'
    assert _resumen_manifiesto(texto, 'mpd') == {'fragmentos': 11, 'suma': None, 'cifrado': 'drm'}
    assert _resumen_manifiesto('<MPD mediaPresentationDuration="PT0H10M54.50S">', 'mpd')['suma'] == 654.5


# ---------- plantillas ----------
def test_plantillas_validadas():
    limpias = validar_plantillas([{'id': 'a', 'nombre': 'A', 'args': '-f b'}, {'id': 'a', 'nombre': 'dup'},
                                  {'id': '../x', 'nombre': 'mala'}, 'basura', {'id': 'b', 'nombre': '', 'args': None}])
    assert limpias == [{'id': 'a', 'nombre': 'A', 'args': '-f b'}, {'id': 'b', 'nombre': 'Plantilla', 'args': ''}]


def test_comando_antiguo_pasa_a_plantilla(tmp_path):
    ruta = tmp_path / 'settings.json'
    ruta.write_text('{"args_extra": "--embed-chapters"}', encoding='utf-8')
    a = Ajustes(str(ruta))
    assert a.get('plantilla_args_id') == 'mio'
    assert a.get('plantillas_args')[0] == {'id': 'mio', 'nombre': 'Mi comando', 'args': '--embed-chapters'}


def test_minimizar_a_bandeja_apagado_por_defecto(tmp_path):
    assert Ajustes(str(tmp_path / 's.json')).get('bandeja_al_minimizar') is False
