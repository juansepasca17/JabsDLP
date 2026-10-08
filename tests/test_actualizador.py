import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jabsdlp import actualizador  # noqa: E402


def test_tupla_compara_estables_y_nightly():
    t = actualizador.tupla
    assert t('2026.08.19') == t('2026.8.19') == (2026, 8, 19)
    assert t('2026.9.27.232945.dev0') == (2026, 9, 27, 232945)
    assert t('2026.8.19') < t('2026.8.19.123.dev0') < t('2026.8.20')
    assert t(None) == ()


def test_es_nightly():
    assert actualizador.es_nightly('2026.9.27.232945.dev0')
    assert actualizador.es_nightly('2026.09.27.232945')
    assert not actualizador.es_nightly('2026.08.19')


def preparar(tmp_path, monkeypatch, incluida, descargada, crear=True):
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    monkeypatch.setattr(actualizador, '_incluida', incluida)
    monkeypatch.setattr(actualizador, '_activa', None)
    archivos = ['yt_dlp-x.whl', 'yt_dlp_ejs-x.whl']
    if crear:
        for a in archivos:
            open(os.path.join(actualizador.carpeta(), a), 'wb').close()
    actualizador.guardar_estado({'version': descargada, 'archivos': archivos})


def test_no_activa_si_la_incluida_es_igual_o_mas_nueva(tmp_path, monkeypatch):
    preparar(tmp_path, monkeypatch, '2026.10.1', '2026.9.27.232945.dev0')
    assert actualizador.activar() is None
    y = actualizador.estado_publico('2026.10.01')
    assert y['reiniciar'] is False and y['actualizada'] is False


def test_no_activa_si_faltan_archivos(tmp_path, monkeypatch):
    preparar(tmp_path, monkeypatch, '2026.8.19', '2026.9.27.232945.dev0', crear=False)
    assert actualizador.activar() is None
    assert actualizador.estado_publico('2026.08.19')['descargada'] is None


def test_descargada_mas_nueva_pide_reiniciar(tmp_path, monkeypatch):
    preparar(tmp_path, monkeypatch, '2026.8.19', '2026.9.27.232945.dev0')
    y = actualizador.estado_publico('2026.08.19')
    assert y['descargada'] == '2026.9.27.232945.dev0' and y['reiniciar'] is True


def test_restaurar_borra_descargas(tmp_path, monkeypatch):
    preparar(tmp_path, monkeypatch, '2026.8.19', '2026.9.27.232945.dev0')
    actualizador.restaurar()
    assert not [f for f in os.listdir(actualizador.carpeta()) if f.endswith('.whl')]
    assert actualizador.leer_estado().get('version') is None
