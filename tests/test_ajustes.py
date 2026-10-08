import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jabsdlp import cookies  # noqa: E402
from jabsdlp.ajustes import Ajustes  # noqa: E402


def nuevos_ajustes(tmp_path):
    return Ajustes(os.path.join(tmp_path, 'settings.json'))


def test_valores_invalidos_se_ignoran(tmp_path):
    a = nuevos_ajustes(tmp_path)
    a.actualizar({'gpu': 'rm -rf', 'max_paralelo': 'x', 'cookies_modo': 'otro', 'desconocida': 1, 'prefs': {'codec': 'evil'}})
    assert a.get('gpu') == 'auto'
    assert a.get('max_paralelo') == 0
    assert a.get('cookies_modo') == 'ninguna'
    assert a.get('prefs')['codec'] == 'auto'
    assert 'desconocida' not in a.todo()


def test_enteros_se_acotan(tmp_path):
    a = nuevos_ajustes(tmp_path)
    a.actualizar({'fragmentos': 500, 'calidad': -3, 'max_paralelo': '7'})
    assert a.get('fragmentos') == 32 and a.get('calidad') == 10 and a.get('max_paralelo') == 7


def test_ffmpeg_solo_acepta_ffmpeg_exe(tmp_path):
    a = nuevos_ajustes(tmp_path)
    malo = os.path.join(tmp_path, 'calc.exe')
    open(malo, 'w').close()
    a.actualizar({'ffmpeg_ruta': malo})
    assert a.get('ffmpeg_ruta') == ''
    bueno = os.path.join(tmp_path, 'ffmpeg.exe')
    open(bueno, 'w').close()
    a.actualizar({'ffmpeg_ruta': bueno})
    assert a.get('ffmpeg_ruta') == bueno
    a.actualizar({'ffmpeg_ruta': str(tmp_path)})
    assert a.get('ffmpeg_ruta') == str(tmp_path)


def test_plantilla_no_sale_de_la_carpeta(tmp_path):
    a = nuevos_ajustes(tmp_path)
    for mala in ('..\\..\\Windows\\%(title)s.%(ext)s', 'C:\\x\\%(title)s.%(ext)s', '/etc/%(title)s', '../%(title)s'):
        a.actualizar({'plantilla': mala})
        assert a.get('plantilla') == '%(title)s.%(ext)s'
    a.actualizar({'plantilla': '%(uploader)s/%(title)s.%(ext)s'})
    assert a.get('plantilla') == '%(uploader)s/%(title)s.%(ext)s'


def test_prefs_antiguas_se_migran(tmp_path):
    ruta = os.path.join(tmp_path, 'settings.json')
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write('{"prefs": {"audio": false, "codec": "h265"}}')
    a = Ajustes(ruta)
    assert a.get('prefs')['audio'] == 'no'
    assert a.get('prefs')['codec'] == 'h265'
    assert a.get('prefs')['criterio'] == 'equilibrado'


def test_cookies_normalizadas_y_limpieza(tmp_path):
    origen = os.path.join(tmp_path, 'cookies.txt')
    with open(origen, 'w', encoding='utf-8') as f:
        f.write('youtube.com\tTRUE\t/\tTRUE\t0\tPREF\tx\n.ejemplo.com\tFALSE\t/\tFALSE\t0\tA\tb\nbasura\n')
    temporal = cookies.normalize_netscape_cookie_file(origen)
    try:
        contenido = open(temporal, encoding='utf-8').read().splitlines()
        assert contenido[0] == '# Netscape HTTP Cookie File'
        assert contenido[1].startswith('.youtube.com\tTRUE')
        assert contenido[2].startswith('.ejemplo.com\tTRUE')
        assert len(contenido) == 3
        assert os.path.basename(temporal).startswith(cookies.PREFIJO_TEMPORAL)
    finally:
        cookies.borrar_temporal(temporal)
    huerfano = tempfile.NamedTemporaryFile(delete=False, prefix=cookies.PREFIJO_TEMPORAL, suffix='.txt')
    huerfano.close()
    cookies.limpiar_temporales_huerfanos()
    assert not os.path.exists(huerfano.name)
