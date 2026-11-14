"""1.7.1: torrents en la pestaña Ver (sin red: se crea un torrent de un archivo local ya completo)."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

lt = pytest.importorskip('libtorrent')

from jabsdlp import ver_torrent  # noqa: E402


@pytest.fixture
def torrents(tmp_path, monkeypatch):
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path / 'local'))
    t = ver_torrent.Torrents(subida_kb=15)
    yield t
    t.cerrar_todo()


def crear_torrent(carpeta, nombre='pelicula.mp4', tamano=3 * 1024 * 1024 + 123):
    archivo = carpeta / nombre
    archivo.write_bytes(bytes((i * 7) % 256 for i in range(tamano)))
    fs = lt.file_storage()
    lt.add_files(fs, str(archivo))
    ct = lt.create_torrent(fs, 256 * 1024)
    lt.set_piece_hashes(ct, str(carpeta))
    ruta = carpeta / 'prueba.torrent'
    ruta.write_bytes(lt.bencode(ct.generate()))
    return ruta, archivo.read_bytes()


def test_ajustes_de_privacidad_de_la_sesion(torrents):
    ajustes = torrents.ses.get_settings()
    assert ajustes['upload_rate_limit'] == 15 * 1024
    assert ajustes['enable_lsd'] is False and ajustes['enable_upnp'] is False and ajustes['enable_natpmp'] is False


def test_lee_rangos_y_al_cerrar_borra_la_cache(torrents, tmp_path):
    origen = tmp_path / 'origen'
    origen.mkdir()
    ruta, contenido = crear_torrent(origen)
    clave = torrents.abrir(str(ruta))
    datos = torrents.datos(clave)
    assert datos['nombre'] == 'pelicula.mp4' and datos['tamano'] == len(contenido)
    # se simula que ya está descargado: copiar el archivo a la caché y forzar la comprobación
    import shutil
    shutil.copy(origen / 'pelicula.mp4', datos['ruta'])
    datos['handle'].force_recheck()
    limite = time.time() + 20
    while not datos['handle'].status().is_seeding and time.time() < limite:
        time.sleep(0.1)
    leido = b''.join(torrents.bloques(clave, 300000, 1300000))
    assert leido == contenido[300000:1300001]
    assert b''.join(torrents.bloques(clave, len(contenido) - 50, len(contenido) - 1)) == contenido[-50:]
    carpeta = datos['carpeta']
    torrents.cerrar(clave)
    time.sleep(1.6)
    assert not os.path.exists(carpeta) and clave not in torrents.activos


def test_torrent_sin_video_se_rechaza(torrents, tmp_path):
    origen = tmp_path / 'docs'
    origen.mkdir()
    ruta, _ = crear_torrent(origen, 'notas.txt', 1000)
    with pytest.raises(ver_torrent.TorrentNoReproducible):
        torrents.abrir(str(ruta))
