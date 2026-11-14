"""1.6.0: stack, colecciones (.jabs), biblioteca y captura rápida."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from jabsdlp import biblioteca, captura  # noqa: E402
from jabsdlp.ajustes import Ajustes  # noqa: E402
from jabsdlp.colecciones import FAVORITOS, ColeccionInvalida, Colecciones, limpiar_item  # noqa: E402


# ---------- colecciones ----------
def test_favoritos_siempre_existe_y_no_se_borra(tmp_path):
    c = Colecciones(str(tmp_path / 'c.json'))
    assert c.lista()[0]['id'] == FAVORITOS
    with pytest.raises(ColeccionInvalida):
        c.borrar(FAVORITOS)
    with pytest.raises(ColeccionInvalida):
        c.renombrar(FAVORITOS, 'x')


def test_crear_agregar_sin_duplicados_reordenar_y_quitar(tmp_path):
    c = Colecciones(str(tmp_path / 'c.json'))
    id_ = c.crear('Clips', [{'url': 'https://youtu.be/a', 'titulo': 'A'}])
    assert c.agregar(id_, [{'url': 'https://youtu.be/a'}, {'url': 'https://youtu.be/b'}, {'url': 'javascript:alert(1)'}]) == 1
    c.reordenar(id_, 1, 0)
    assert [i['url'] for i in c.obtener(id_)['items']] == ['https://youtu.be/b', 'https://youtu.be/a']
    c.quitar(id_, {'url': 'https://youtu.be/b'})
    assert len(Colecciones(str(tmp_path / 'c.json')).obtener(id_)['items']) == 1   # se guardó en disco


def test_favorito_de_archivo_local(tmp_path):
    c = Colecciones(str(tmp_path / 'c.json'))
    ruta = str(tmp_path / 'video.mp4')
    assert c.alternar_favorito({'ruta': ruta}) is True
    assert os.path.normcase(ruta) in c.favoritos_rutas()
    assert c.alternar_favorito({'ruta': ruta}) is False


def test_limpiar_item_rechaza_lo_peligroso():
    assert limpiar_item({'url': 'file:///C:/Windows/x.exe'}) is None
    assert limpiar_item({'url': 'https://a.com/x y'}) is None
    assert limpiar_item({'ruta': 'relativa/x.mp4'}) is None
    assert limpiar_item({'ruta': 'C:\\x.mp4'}, permitir_rutas=False) is None
    item = limpiar_item({'url': 'https://a.com/v', 'titulo': 'x' * 999, 'miniatura': 'http://inseguro/x.jpg', 'duracion': '12'})
    assert len(item['titulo']) == 300 and 'miniatura' not in item and item['duracion'] == 12.0


def test_exportar_e_importar_jabs(tmp_path):
    c = Colecciones(str(tmp_path / 'c.json'))
    id_ = c.crear('Clips de Juanito', [{'url': 'https://youtu.be/a', 'titulo': 'A', 'visto': True, 'posicion': 30},
                                       {'ruta': str(tmp_path / 'local.mp4'), 'titulo': 'Local'}])
    destino = str(tmp_path / 'clips.jabs')
    r = c.exportar(id_, destino)
    assert r == {'exportados': 1, 'omitidos': 1}
    datos = json.loads(open(destino, encoding='utf-8').read())
    assert datos['formato'] == 'jabsdlp-coleccion' and 'visto' not in datos['items'][0]   # sin progreso por defecto
    otra = Colecciones(str(tmp_path / 'otra.json'))
    nuevo, cantidad = otra.importar(destino)
    assert cantidad == 1 and otra.obtener(nuevo)['nombre'] == 'Clips de Juanito'


def test_importar_txt_y_archivos_malos(tmp_path):
    c = Colecciones(str(tmp_path / 'c.json'))
    txt = tmp_path / 'lista.txt'
    txt.write_text('https://youtu.be/a\nbasura\nhttps://vimeo.com/1\n', encoding='utf-8')
    assert c.importar(str(txt))[1] == 2
    malo = tmp_path / 'malo.jabs'
    malo.write_text('{"formato": "otra-cosa", "items": []}', encoding='utf-8')
    with pytest.raises(ColeccionInvalida):
        c.importar(str(malo))
    rutas = tmp_path / 'rutas.jabs'
    rutas.write_text(json.dumps({'formato': 'jabsdlp-coleccion', 'items': [{'ruta': 'C:\\Windows\\x.exe'}]}), encoding='utf-8')
    with pytest.raises(ColeccionInvalida):   # un .jabs nunca trae rutas locales
        c.importar(str(rutas))


# ---------- biblioteca ----------
def test_biblioteca_lista_medios_y_rechaza_salir_de_la_carpeta(tmp_path):
    (tmp_path / 'a.mp4').write_bytes(b'x')
    (tmp_path / 'b.mp3').write_bytes(b'x')
    (tmp_path / 'c.exe').write_bytes(b'x')
    (tmp_path / 'd.mp4.part').write_bytes(b'x')
    (tmp_path / 'sub').mkdir()
    datos = biblioteca.listar(str(tmp_path))
    assert sorted(a['nombre'] for a in datos['archivos']) == ['a.mp4', 'b.mp3']
    assert [c['nombre'] for c in datos['carpetas']] == ['sub']
    with pytest.raises(biblioteca.RutaNoPermitida):
        biblioteca.listar(str(tmp_path / 'sub'), '..')
    assert not biblioteca.dentro_de('C:\\Windows', [str(tmp_path)])


def test_carpetas_de_biblioteca_validadas(tmp_path):
    a = Ajustes(str(tmp_path / 's.json'))
    a.actualizar({'carpetas_biblioteca': [str(tmp_path), str(tmp_path), 'C:\\no\\existe', 5]})
    assert a.get('carpetas_biblioteca') == [str(tmp_path)]


# ---------- captura ----------
def test_teclas_del_atajo():
    assert captura.interpretar_tecla('ctrl+alt+x') == (0x3, 0x58)
    for malo in ('x', 'ctrl+alt+z', 'win+x', ''):
        with pytest.raises(ValueError):
            captura.interpretar_tecla(malo)


def test_sitio_reconocido():
    assert captura.sitio_reconocido('https://www.youtube.com/watch?v=jNQXAC9IVRw')
    assert not captura.sitio_reconocido('https://www.google.com/search?q=hola')


def test_ajustes_16_por_defecto_desactivados(tmp_path):
    a = Ajustes(str(tmp_path / 's.json'))
    for clave in ('modo_stack', 'stack_auto', 'captura_atajo', 'captura_portapapeles', 'pantalla_completa'):
        assert a.get(clave) is False
    assert a.get('boton_colecciones') == 'lateral' and a.get('captura_modo') == 'sugerir'
