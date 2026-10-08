import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jabsdlp import formatos  # noqa: E402
from jabsdlp.ajustes import PREFS_POR_DEFECTO  # noqa: E402


def video(fid, h, vcodec, size, fps=30, protocol='https', **extra):
    return {'format_id': fid, 'ext': 'mp4', 'vcodec': vcodec, 'acodec': 'none', 'height': h, 'width': h * 16 // 9,
            'fps': fps, 'tbr': (size or 31_000_000) * 8 / 1000 / 100, 'filesize': size, 'protocol': protocol, **extra}


def audio(fid, acodec, abr, size, **extra):
    return {'format_id': fid, 'ext': 'webm' if acodec == 'opus' else 'm4a', 'vcodec': 'none', 'acodec': acodec,
            'abr': abr, 'tbr': abr, 'filesize': size, 'protocol': 'https', 'language_preference': -1, **extra}


INFO = {
    'duration': 100,
    'formats': [
        {'format_id': 'sb0', 'ext': 'mhtml', 'vcodec': 'none', 'acodec': 'none', 'format_note': 'storyboard'},
        audio('140', 'mp4a.40.2', 129, 1_600_000),
        audio('139', 'mp4a.40.5', 49, 600_000),
        audio('251', 'opus', 130, 1_550_000),
        audio('250', 'opus', 70, 850_000),
        audio('249', 'opus', 50, 620_000),
        audio('251-drc', 'opus', 131, 1_560_000, format_note='medium, DRC'),
        video('137', 1080, 'avc1.640028', 40_000_000),
        video('248', 1080, 'vp9', 30_000_000),
        video('399', 1080, 'av01.0.08M.08', 25_000_000),
        video('614', 1080, 'vp09.00.40.08', None, protocol='m3u8_native'),
        video('136', 720, 'avc1.4d401f', 20_000_000),
        video('398', 720, 'av01.0.05M.08', 12_000_000),
        video('298', 720, 'avc1.4d4020', 26_000_000, fps=60),
        video('401', 2160, 'av01.0.12M.08', 120_000_000),
        video('701', 2160, 'av01.0.12M.10', 150_000_000, dynamic_range='HDR10'),
    ],
}


def prefs(**cambios):
    return {**PREFS_POR_DEFECTO, **cambios}


def test_familias():
    assert formatos.familia_video('av01.0.08M.08') == 'av1'
    assert formatos.familia_video('vp09.00.40.08') == 'vp9'
    assert formatos.familia_video('hvc1.1.6.L120') == 'h265'
    assert formatos.familia_video('avc1.640028') == 'h264'
    assert formatos.familia_video('none') is None
    assert formatos.familia_audio('mp4a.40.2') == 'aac'
    assert formatos.familia_audio('opus') == 'opus'


def test_storyboard_se_ignora():
    assert formatos.clase(INFO['formats'][0]) is None


def test_recomendado_auto_maxima_resolucion_sdr_mejor_codec():
    r = formatos.calcular(INFO, prefs())['recomendado']
    assert r['altura'] == 2160
    assert r['hdr'] is False
    assert r['spec'] == '401+251'
    assert r['contenedor'] == 'mp4'
    assert r['recodificar'] is None
    assert 'Mejor códec' in r['etiquetas']


def test_recomendado_1080_es_av1_el_mas_pequeno():
    r = formatos.calcular(INFO, prefs(resolucion='1080'))['recomendado']
    assert r['spec'] == '399+251'
    assert r['tamano'] == 25_000_000 + 1_550_000
    assert set(r['etiquetas']) == {'Equilibrado', 'Mejor códec', 'Menor tamaño'}


def test_resolucion_inexistente_usa_la_inferior_mas_cercana():
    r = formatos.calcular(INFO, prefs(resolucion='1440'))['recomendado']
    assert r['altura'] == 1080


def test_preferir_h264_existente_sin_recodificar_y_con_aac():
    r = formatos.calcular(INFO, prefs(resolucion='1080', codec='h264'))['recomendado']
    assert r['spec'] == '137+140'
    assert r['recodificar'] is None


def test_h265_no_disponible_se_recodifica():
    r = formatos.calcular(INFO, prefs(resolucion='1080', codec='h265'))['recomendado']
    assert r['vcodec'] == 'av1'
    assert r['recodificar'] == 'h265'
    assert r['contenedor'] == 'mp4'


def test_vp9_no_disponible_en_720_avisa():
    r = formatos.calcular(INFO, prefs(resolucion='720', codec='vp9'))['recomendado']
    assert r['vcodec'] == 'h264' and r['fps'] == 60  # en 720p solo hay 60 fps en H.264
    assert r['aviso']


def test_sin_audio_solo_video():
    r = formatos.calcular(INFO, prefs(resolucion='1080', audio='no'))['recomendado']
    assert r['spec'] == '399'
    assert r['audio'] is False


def test_duplicado_m3u8_se_descarta():
    specs = [o['spec'] for o in formatos.calcular(INFO, prefs())['opciones']]
    assert not any(s.startswith('614') for s in specs)
    assert any(s.startswith('248') for s in specs)


def test_webm_incompatible_con_h264_cae_a_mkv():
    assert formatos.contenedor_para('h264', 'aac', 'webm') == 'mkv'
    assert formatos.contenedor_para('vp9', 'opus', 'webm') == 'webm'
    assert formatos.contenedor_para('av1', 'opus', 'auto') == 'mp4'
    assert formatos.contenedor_para('av1', 'opus', 'webm', recodificar='h265') == 'mkv'


def test_audio_auto_opus_sin_drc():
    r = formatos.calcular(INFO, prefs(tipo='audio'))['recomendado']
    assert r['spec'] == '251'
    assert r['contenedor'] == 'opus'
    assert r['recodificar'] is None


def test_audio_m4a_prefiere_aac_sin_recodificar():
    r = formatos.calcular(INFO, prefs(tipo='audio', formato_audio='m4a'))['recomendado']
    assert r['spec'] == '140'
    assert r['recodificar'] is None


def test_audio_mp3_recodifica():
    r = formatos.calcular(INFO, prefs(tipo='audio', formato_audio='mp3'))['recomendado']
    assert r['recodificar'] == 'mp3'
    assert r['contenedor'] == 'mp3'


def test_selector_playlist():
    fmt, orden = formatos.selector_por_preferencias(prefs(resolucion='1080'))
    assert fmt.startswith('bv+ba') or fmt.startswith('bv')
    assert 'res:1080' in orden and '+size' in orden and 'hdr:sdr' in orden
    fmt, _ = formatos.selector_por_preferencias(prefs(codec='h264'))
    assert "vcodec~='^(avc1|avc3|h264)'" in fmt and '[acodec^=mp4a]' in fmt
    assert fmt.split('/')[0].count('[format_id!*=drc]') == 1
    fmt, _ = formatos.selector_por_preferencias(prefs(audio='no'))
    assert '+ba' not in fmt
    fmt, orden = formatos.selector_por_preferencias(prefs(tipo='audio', formato_audio='opus'))
    assert fmt.startswith('ba[format_id!*=drc][acodec=opus]')


def test_necesita_recodificar():
    assert formatos.necesita_recodificar('av01.0.08M.08', prefs(codec='h265')) == 'h265'
    assert formatos.necesita_recodificar('hvc1.1.6', prefs(codec='h265')) is None
    assert formatos.necesita_recodificar('av01', prefs(codec='auto')) is None
    assert formatos.necesita_recodificar('av01', prefs(codec='h265', tipo='audio')) is None


def test_audio_antiguo_booleano_se_normaliza():
    assert formatos.normalizar({'audio': True})['audio'] == 'auto'
    assert formatos.normalizar({'audio': False})['audio'] == 'no'
    assert formatos.normalizar({})['criterio'] == 'equilibrado'


def test_criterio_ahorro_baja_a_720_menos_fps_y_audio_medio():
    r = formatos.calcular(INFO, prefs(criterio='ahorro'))['recomendado']
    assert r['altura'] == 720
    assert r['fps'] == 30
    assert r['spec'] == '398+250'
    assert 'Ahorro' in r['etiquetas']


def test_criterio_ahorro_respeta_resolucion_elegida():
    r = formatos.calcular(INFO, prefs(criterio='ahorro', resolucion='1080'))['recomendado']
    assert r['altura'] == 1080
    assert r['spec'] == '399+250'


def test_criterio_calidad_elige_mayor_bitrate():
    r = formatos.calcular(INFO, prefs(criterio='calidad', resolucion='1080'))['recomendado']
    assert r['spec'] == '137+251'
    assert 'Máxima calidad' in r['etiquetas']


def test_audio_personalizado_por_pista_y_por_nivel():
    c = formatos.calcular(INFO, prefs(resolucion='1080', audio='custom'), audio_id='249')
    assert c['audio_elegido'] == '249'
    assert c['recomendado']['spec'] == '399+249'
    assert {a['spec'] for a in c['audios']} >= {'251', '250', '249', '140', '139'}
    c = formatos.calcular(INFO, prefs(resolucion='1080', audio='custom', audio_calidad='media'))
    assert c['audio_elegido'] == '250'
    c = formatos.calcular(INFO, prefs(resolucion='1080', audio='custom', audio_calidad='baja'))
    assert c['audio_elegido'] == '249'


def test_sin_audio_no_lista_pistas():
    c = formatos.calcular(INFO, prefs(audio='no'))
    assert c['audios'] == [] and c['audio_elegido'] is None


def test_selector_criterios_y_audio():
    fmt, orden = formatos.selector_por_preferencias(prefs(criterio='ahorro'))
    assert 'res:720' in orden and '+fps' in orden and '[abr<=?100]' in fmt
    fmt, orden = formatos.selector_por_preferencias(prefs(criterio='calidad'))
    assert 'tbr' in orden and '+size' not in orden
    fmt, _ = formatos.selector_por_preferencias(prefs(audio='custom', audio_calidad='baja'))
    assert '[abr<=?64]' in fmt


def test_audio_criterios():
    r = formatos.calcular(INFO, prefs(tipo='audio', criterio='ahorro'))['recomendado']
    assert r['spec'] == '250'
    r = formatos.calcular(INFO, prefs(tipo='audio', criterio='calidad'))['recomendado']
    assert r['spec'] == '251'
