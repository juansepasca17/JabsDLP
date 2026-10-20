import hashlib
import os
import sys
from contextlib import contextmanager

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
    archivos = [f'yt_dlp-{descargada}-py3-none-any.whl', 'yt_dlp_ejs-0.8.0-py3-none-any.whl']
    if crear:
        for a in archivos:
            open(os.path.join(actualizador.carpeta(), a), 'wb').close()
    vacio = hashlib.sha256(b'').hexdigest()
    actualizador.guardar_estado({'version': descargada, 'archivos': archivos, 'sha256': {a: vacio for a in archivos}})


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


@contextmanager
def proceso_limpio():
    """activar() toca sys.meta_path y sys.path; se restauran al salir para no teñir otros tests."""
    meta, path = list(sys.meta_path), list(sys.path)
    try:
        yield
    finally:
        sys.meta_path[:] = meta
        sys.path[:] = path
        actualizador._activa = None
        actualizador._buscador = None


def _sin_red(*args, **kwargs):
    raise AssertionError('no debe ir a la red')


def test_activar_con_descargada_mas_nueva_instala_el_finder(tmp_path, monkeypatch):
    preparar(tmp_path, monkeypatch, '2026.8.19', '2026.9.27.232945.dev0')
    with proceso_limpio():
        assert actualizador.activar() == '2026.9.27.232945.dev0'
        # el finder gana a cualquier otro importador: va el primero en sys.meta_path
        assert sys.meta_path[0] is actualizador._buscador
        # y los .whl quedan en sys.path por delante (importlib.metadata y recursos)
        assert sys.path[0] == os.path.join(actualizador.carpeta(), 'yt_dlp-2026.9.27.232945.dev0-py3-none-any.whl')
    assert actualizador._buscador is None and actualizador._activa is None


def test_desactivar_guarda_motivo_y_version_rota(tmp_path, monkeypatch):
    preparar(tmp_path, monkeypatch, '2026.8.19', '2026.9.27.232945.dev0')
    with proceso_limpio():
        assert actualizador.activar()
        buscador = actualizador._buscador
        actualizador.desactivar('x' * 600)  # el motivo se trunca a 500
        assert buscador not in sys.meta_path
        assert actualizador._activa is None and actualizador._buscador is None
    estado = actualizador.leer_estado()
    assert estado['roto'] is True
    assert estado['version_rota'] == '2026.9.27.232945.dev0'
    assert estado['motivo'] == 'x' * 500


def test_actualizar_no_reintenta_version_rota(tmp_path, monkeypatch):
    preparar(tmp_path, monkeypatch, '2026.8.19', '2026.9.27.232945.dev0')
    estado = actualizador.leer_estado()
    estado.update({'roto': True, 'version_rota': '2026.9.27.232945.dev0', 'motivo': 'boom'})
    actualizador.guardar_estado(estado)
    monkeypatch.setattr(actualizador, 'ultima_version', lambda canal: '2026.9.27.232945.dev0')
    monkeypatch.setattr(actualizador, '_json', _sin_red)
    r = actualizador.actualizar('nightly')
    assert r['estado'] == 'al_dia'
    assert 'falló al cargar' in r['mensaje'] and '2026.9.27.232945.dev0' in r['mensaje']
    tras = actualizador.leer_estado()
    assert tras['roto'] is True and tras['version_rota'] == '2026.9.27.232945.dev0'


def test_actualizar_no_reintenta_roto_con_estado_de_la_130(tmp_path, monkeypatch):
    # Un estado escrito por la 1.3.0 tiene 'roto' pero no 'version_rota': se usa 'version'
    preparar(tmp_path, monkeypatch, '2026.8.19', '2026.9.27.232945.dev0')
    estado = actualizador.leer_estado()
    estado['roto'] = True
    actualizador.guardar_estado(estado)
    monkeypatch.setattr(actualizador, 'ultima_version', lambda canal: '2026.9.27.232945.dev0')
    monkeypatch.setattr(actualizador, '_json', _sin_red)
    r = actualizador.actualizar('nightly')
    assert 'falló al cargar' in r['mensaje'] and '2026.9.27.232945.dev0' in r['mensaje']
    assert actualizador.leer_estado()['roto'] is True


def test_actualizar_descarga_cuando_hay_mas_nueva(tmp_path, monkeypatch):
    preparar(tmp_path, monkeypatch, '2026.8.19', '2026.9.27.232945.dev0')
    estado = actualizador.leer_estado()
    estado.update({'roto': True, 'version_rota': '2026.9.27.232945.dev0', 'motivo': 'boom'})
    actualizador.guardar_estado(estado)
    monkeypatch.setattr(actualizador, 'ultima_version', lambda canal: '2026.10.5')
    monkeypatch.setattr(actualizador, '_json',
                        lambda url: {'info': {'requires_dist': []},
                                     'urls': [{'packagetype': 'bdist_wheel', 'filename': 'yt_dlp-nuevo.whl',
                                               'url': 'http://ejemplo/yt_dlp-nuevo.whl',
                                               'digests': {'sha256': '0'}}]})
    descargados = []

    def _descargar(archivo, destino, progreso_base, peso):
        descargados.append(archivo['filename'])
        open(destino, 'wb').close()

    monkeypatch.setattr(actualizador, '_descargar', _descargar)
    r = actualizador.actualizar('nightly')
    assert r['estado'] == 'listo'
    assert descargados == ['yt_dlp-nuevo.whl']
    tras = actualizador.leer_estado()
    assert tras['version'] == '2026.10.5'
    assert 'roto' not in tras and 'version_rota' not in tras and 'motivo' not in tras


def test_estado_json_corrupto_no_rompe_activar(tmp_path, monkeypatch):
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    monkeypatch.setattr(actualizador, '_incluida', '2026.8.19')
    monkeypatch.setattr(actualizador, '_activa', None)
    ruta = os.path.join(actualizador.carpeta(), 'estado.json')
    for contenido in ('{esto no es json', '[]'):  # JSON roto o con forma inesperada
        with open(ruta, 'w', encoding='utf-8') as f:
            f.write(contenido)
        assert actualizador.leer_estado() == {}
        assert actualizador.activar() is None
        y = actualizador.estado_publico('2026.8.19')
        assert y['descargada'] is None and y['roto'] is False
        assert y['motivo_roto'] is None and y['version_rota'] is None


def test_estado_publico_expone_motivo_roto(tmp_path, monkeypatch):
    preparar(tmp_path, monkeypatch, '2026.8.19', '2026.9.27.232945.dev0')
    estado = actualizador.leer_estado()
    estado.update({'roto': True, 'version_rota': '2026.9.27.232945.dev0', 'motivo': 'ModuleNotFoundError: x'})
    actualizador.guardar_estado(estado)
    y = actualizador.estado_publico('2026.8.19')
    assert y['roto'] is True and y['motivo_roto'] == 'ModuleNotFoundError: x'
    assert y['version_rota'] == '2026.9.27.232945.dev0'
    assert y['reiniciar'] is False
    preparar(tmp_path, monkeypatch, '2026.8.19', '2026.9.27.232945.dev0')  # sin roto: nada que informar
    y = actualizador.estado_publico('2026.8.19')
    assert y['roto'] is False and y['motivo_roto'] is None and y['version_rota'] is None


def test_actualizar_nightly_sin_descargables_da_error_claro(tmp_path, monkeypatch):
    preparar(tmp_path, monkeypatch, '2026.8.19', '2026.8.19')
    respuestas = [
        {'info': {'version': '2026.8.19'}, 'releases': {}},  # sin releases
        {'info': {'version': '2026.8.19'},
         'releases': {'2026.8.19': [{'packagetype': 'bdist_wheel', 'yanked': True}]}},  # todo yanked
    ]
    for respuesta in respuestas:
        monkeypatch.setattr(actualizador, '_json', lambda url, r=respuesta: r)
        r = actualizador.actualizar('nightly')
        assert r['estado'] == 'error'
        assert 'PyPI no devolvió ninguna versión descargable.' in r['mensaje']


def test_restaurar_borra_tambien_error_carga(tmp_path, monkeypatch):
    preparar(tmp_path, monkeypatch, '2026.8.19', '2026.9.27.232945.dev0')
    ruta = os.path.join(actualizador.carpeta(), 'error-carga.txt')
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write('traceback')
    actualizador.restaurar()
    assert not os.path.exists(ruta)


def test_no_carga_ruedas_con_rutas_manipuladas(tmp_path, monkeypatch):
    preparar(tmp_path, monkeypatch, '2026.8.19', '2026.9.27.232945.dev0')
    for malo in (r'..\..\evil-py3-none-any.whl', r'C:\x\yt_dlp-1-py3-none-any.whl', '../yt_dlp-1-py3-none-any.whl',
                 'yt_dlp-1-py3-none-any.whl.exe', 'otro-1-py3-none-any.whl'):
        assert not actualizador.nombre_valido(malo)
        estado = actualizador.leer_estado()
        estado['archivos'] = [malo]
        estado['sha256'] = {malo: hashlib.sha256(b'').hexdigest()}
        actualizador.guardar_estado(estado)
        assert actualizador.activar() is None


def test_no_activa_si_el_sha_no_coincide(tmp_path, monkeypatch):
    preparar(tmp_path, monkeypatch, '2026.8.19', '2026.9.27.232945.dev0')
    estado = actualizador.leer_estado()
    with open(os.path.join(actualizador.carpeta(), estado['archivos'][0]), 'wb') as f:
        f.write(b'codigo alterado')
    assert actualizador.activar() is None


def test_estado_antiguo_sin_sumas_no_se_activa(tmp_path, monkeypatch):
    preparar(tmp_path, monkeypatch, '2026.8.19', '2026.9.27.232945.dev0')
    estado = actualizador.leer_estado()
    del estado['sha256']
    actualizador.guardar_estado(estado)
    assert actualizador.activar() is None


def test_descarga_rechaza_nombre_o_host_no_validos(tmp_path, monkeypatch):
    import pytest
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    malos = [{'filename': '../x-py3-none-any.whl', 'url': 'https://files.pythonhosted.org/x', 'digests': {'sha256': ''}},
             {'filename': 'yt_dlp-1-py3-none-any.whl', 'url': 'https://evil.example/x.whl', 'digests': {'sha256': ''}}]
    for archivo in malos:
        with pytest.raises(RuntimeError):
            actualizador._descargar(archivo, os.path.join(actualizador.carpeta(), 'x.whl'), 0, 1)
