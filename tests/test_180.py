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
