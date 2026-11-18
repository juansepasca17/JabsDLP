"""1.8.0: al cancelar un torrent se borra solo lo que creó aria2 para él."""
import os

from jabsdlp.trabajo import _borrar_torrent_parcial


def test_borra_carpeta_y_aria2_del_torrent(tmp_path):
    (tmp_path / 'viejo.mp4').write_text('x')
    antes = set(os.listdir(tmp_path))
    (tmp_path / 'Pelicula').mkdir()
    (tmp_path / 'Pelicula' / 'parte.mkv').write_text('x')
    (tmp_path / 'Pelicula.aria2').write_text('x')
    (tmp_path / 'otra descarga.mp4').write_text('x')   # apareció mientras tanto: no es del torrent
    _borrar_torrent_parcial(str(tmp_path), antes)
    assert sorted(os.listdir(tmp_path)) == ['otra descarga.mp4', 'viejo.mp4']


def test_archivo_suelto_del_torrent(tmp_path):
    antes = set()
    (tmp_path / 'video.mp4').write_text('x')
    (tmp_path / 'video.mp4.aria2').write_text('x')
    _borrar_torrent_parcial(str(tmp_path), antes)
    assert os.listdir(tmp_path) == []


def test_magnet_cancelado_deja_carpeta_vacia(tmp_path):
    antes = set()
    (tmp_path / 'Serie' / 'Temporada 1').mkdir(parents=True)   # aria2 la creó y aún no escribió nada
    (tmp_path / 'mio').mkdir()
    (tmp_path / 'mio' / 'nota.txt').write_text('x')             # carpeta con archivos: no se toca
    _borrar_torrent_parcial(str(tmp_path), antes)
    assert os.listdir(tmp_path) == ['mio']


def _api(tmp_path, monkeypatch):
    import json
    monkeypatch.setenv('APPDATA', str(tmp_path))
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path / 'local'))
    (tmp_path / 'JabsDLP').mkdir(exist_ok=True)
    descargas = tmp_path / 'Descargas'
    descargas.mkdir()
    (tmp_path / 'JabsDLP' / 'settings.json').write_text(
        json.dumps({'ytdlp_auto': False, 'carpeta': str(descargas)}), encoding='utf-8')
    from jabsdlp.api import Api
    return Api(), descargas


def test_stack_sin_carpeta_aparte_por_defecto(tmp_path, monkeypatch):
    api, _ = _api(tmp_path, monkeypatch)
    agregados = []
    monkeypatch.setattr(api._gestor, 'agregar', lambda trabajos: agregados.extend(trabajos))
    items = [{'url': 'https://www.youtube.com/watch?v=aqz-KE-bpKQ', 'titulo': 'Video'}]
    assert api.descargar({'tipo': 'stack', 'nombre': 'Stack', 'prefs': {}, 'items': items})['ok']
    assert agregados[0].subcarpeta is None and not agregados[0].prefs.get('_stack')
    api.guardar_ajustes({'stack_subcarpeta': True})
    assert api.descargar({'tipo': 'stack', 'nombre': 'Stack', 'prefs': {}, 'items': items})['ok']
    assert agregados[1].subcarpeta == 'Stack' and agregados[1].prefs.get('_stack')
    api.cerrar()


def test_borrar_carpeta_vacia_de_la_biblioteca(tmp_path, monkeypatch):
    api, descargas = _api(tmp_path, monkeypatch)
    (descargas / 'vacia').mkdir()
    (descargas / 'llena').mkdir()
    (descargas / 'llena' / 'a.txt').write_text('x')
    assert api.biblioteca_borrar_carpeta(str(descargas), 'vacia')['ok']
    assert not (descargas / 'vacia').exists()
    assert not api.biblioteca_borrar_carpeta(str(descargas), 'llena')['ok']   # con archivos: no
    assert not api.biblioteca_borrar_carpeta(str(descargas), '')['ok']        # la raíz: nunca
    assert not api.biblioteca_borrar_carpeta(str(descargas), '../JabsDLP')['ok']
    api.cerrar()
