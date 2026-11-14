"""Torrents en la pestaña Ver: reproducir mientras se descarga, sin compartir al cerrar.

- Se descarga en orden (sequential) solo el archivo de video elegido (el más grande), en una caché temporal.
- El proxy local sirve ese archivo con Range: al pedir un trozo se priorizan sus piezas (set_piece_deadline) y se
  espera a tenerlas, así se puede saltar en la línea de tiempo.
- Mientras se reproduce, la subida queda limitada (Ajustes → Red → subida máxima en torrents). Al cerrar el
  reproductor el torrent se quita y la caché se borra: no se sigue compartiendo.
"""
import os
import shutil
import threading
import time
import urllib.request

from .ajustes import carpeta_local

EXT_VIDEO = ('.mp4', '.mkv', '.webm', '.avi', '.mov', '.m4v', '.ts', '.wmv', '.flv', '.mpg', '.mpeg')
EXT_AUDIO = ('.mp3', '.flac', '.m4a', '.ogg', '.opus', '.wav', '.aac')
EXT_SUBS = ('.srt', '.vtt')
ESPERA_METADATOS = 90      # s para recibir la información de un magnet
ESPERA_PIEZA = 120         # s como mucho esperando una pieza antes de rendirse
VENTANA = 8 * 1024 * 1024   # bytes que se priorizan por delante de lo que pide el reproductor


class TorrentNoReproducible(ValueError):
    pass


def carpeta_cache():
    ruta = os.path.join(carpeta_local(), 'ver-cache')
    os.makedirs(ruta, exist_ok=True)
    return ruta


def limpiar_cache():
    """Borra restos de sesiones anteriores (si la app se cerró de golpe)."""
    shutil.rmtree(os.path.join(carpeta_local(), 'ver-cache'), ignore_errors=True)


class Torrents:
    def __init__(self, subida_kb=20):
        import libtorrent as lt
        self.lt = lt
        self.ses = lt.session({
            'listen_interfaces': '0.0.0.0:0,[::]:0',
            'user_agent': 'JabsDLP',
            'enable_dht': True, 'enable_lsd': False, 'enable_upnp': False, 'enable_natpmp': False,
            'upload_rate_limit': max(1, int(subida_kb)) * 1024,
            # El límite es para los datos de video que compartes; el tráfico del protocolo (incluidas las peticiones
            # de piezas, que también es subida) no se limita: si no, la descarga se estrangula
            'rate_limit_ip_overhead': False,
            'alert_mask': 0,
        })
        self.activos = {}      # clave -> dict(handle, archivo, ruta, tamano, inicio_archivo, pieza, carpeta)
        self._lock = threading.Lock()

    def limite_subida(self, kb):
        self.ses.apply_settings({'upload_rate_limit': max(1, int(kb)) * 1024})

    # ---------- abrir ----------
    def abrir(self, origen):
        """origen: magnet, URL a un .torrent o ruta local. Devuelve la clave del torrent abierto."""
        lt = self.lt
        clave = os.urandom(6).hex()
        carpeta = os.path.join(carpeta_cache(), clave)
        os.makedirs(carpeta, exist_ok=True)
        if origen.lower().startswith('magnet:?'):
            params = lt.parse_magnet_uri(origen)
        else:
            if origen.lower().startswith(('http://', 'https://')):
                peticion = urllib.request.Request(origen, headers={'User-Agent': 'JabsDLP'})
                with urllib.request.urlopen(peticion, timeout=30) as r:
                    datos = r.read(20 * 1024 * 1024 + 1)
                if len(datos) > 20 * 1024 * 1024:
                    raise TorrentNoReproducible('El archivo .torrent es demasiado grande.')
                info = lt.torrent_info(lt.bdecode(datos))
            else:
                info = lt.torrent_info(origen)
            params = lt.add_torrent_params()
            params.ti = info
        params.save_path = carpeta
        params.flags |= lt.torrent_flags.sequential_download   # hasta tener la información y el principio
        params.flags &= ~lt.torrent_flags.auto_managed
        params.flags &= ~lt.torrent_flags.paused   # sin esto un magnet nunca recibe su información
        h = self.ses.add_torrent(params)
        limite = time.time() + ESPERA_METADATOS
        while not h.status().has_metadata:
            if time.time() > limite:
                self.ses.remove_torrent(h, lt.options_t.delete_files)
                shutil.rmtree(carpeta, ignore_errors=True)
                raise TorrentNoReproducible('No llegó la información del torrent (pocos pares o enlace caducado).')
            time.sleep(0.25)
        ti = h.torrent_file()
        archivos = ti.files()
        candidatos = [(archivos.file_size(i), i) for i in range(archivos.num_files())
                      if archivos.file_path(i).lower().endswith(EXT_VIDEO + EXT_AUDIO)]
        if not candidatos:
            self.ses.remove_torrent(h, lt.options_t.delete_files)
            shutil.rmtree(carpeta, ignore_errors=True)
            raise TorrentNoReproducible('Este torrent no tiene ningún video ni audio para reproducir.')
        _, elegido = max(candidatos)
        subs = [i for i in range(archivos.num_files()) if archivos.file_path(i).lower().endswith(EXT_SUBS)
                and archivos.file_size(i) < 2 * 1024 * 1024][:8]
        prioridades = [0] * archivos.num_files()
        prioridades[elegido] = 7
        for i in subs:
            prioridades[i] = 7
        h.prioritize_files(prioridades)
        # A partir de aquí manda lo que pide el reproductor (set_piece_deadline), no el orden: así saltar es rápido
        h.unset_flags(lt.torrent_flags.sequential_download)
        h.resume()
        with self._lock:
            self.activos[clave] = {
                'handle': h, 'archivo': elegido, 'carpeta': carpeta,
                'ruta': os.path.join(carpeta, archivos.file_path(elegido)),
                'nombre': os.path.basename(archivos.file_path(elegido)),
                'tamano': archivos.file_size(elegido), 'inicio': archivos.file_offset(elegido),
                'pieza': ti.piece_length(), 'piezas': ti.num_pieces(), 'titulo': ti.name(),
                'subs': [os.path.join(carpeta, archivos.file_path(i)) for i in subs],
            }
        return clave

    def datos(self, clave):
        return self.activos.get(clave)

    # ---------- leer con Range ----------
    def bloques(self, clave, inicio, fin, cancelado=lambda: False):
        """Genera los bytes [inicio, fin] del archivo elegido, esperando (y priorizando) cada pieza."""
        t = self.activos.get(clave)
        if t is None:
            return
        h, tam_pieza = t['handle'], t['pieza']
        posicion = inicio
        avisadas = -1
        # Un salto (petición lejos de la anterior): se olvidan las prioridades viejas
        ultima_pos = t.get('ultima_pos')
        if ultima_pos is not None and abs(inicio - ultima_pos) > VENTANA:
            try:
                h.clear_piece_deadlines()
            except Exception:  # noqa: BLE001
                pass
        t['ultima_pos'] = inicio
        while posicion <= fin:
            absoluta = t['inicio'] + posicion
            pieza = absoluta // tam_pieza
            if pieza > avisadas:
                # priorizar la ventana que viene (la primera, cuanto antes)
                ultima = min(t['piezas'] - 1, (t['inicio'] + min(fin, posicion + VENTANA)) // tam_pieza)
                for n, p in enumerate(range(pieza, ultima + 1)):
                    h.set_piece_deadline(p, 20 + n * 100)
                avisadas = ultima
                t['ultima_pos'] = posicion
            limite = time.time() + ESPERA_PIEZA
            while not h.have_piece(pieza):
                if cancelado() or clave not in self.activos or time.time() > limite:
                    return
                time.sleep(0.05)
            fin_pieza = (pieza + 1) * tam_pieza - t['inicio'] - 1
            hasta = min(fin, fin_pieza, t['tamano'] - 1)
            try:
                with open(t['ruta'], 'rb') as f:
                    f.seek(posicion)
                    restante = hasta - posicion + 1
                    while restante > 0:
                        trozo = f.read(min(256 * 1024, restante))
                        if not trozo:
                            break
                        yield trozo
                        restante -= len(trozo)
                        posicion += len(trozo)
            except OSError:
                time.sleep(0.2)   # la pieza está pero el disco aún no la escribió: reintentar
                continue
            if posicion <= hasta:
                time.sleep(0.1)

    def estado(self, clave):
        t = self.activos.get(clave)
        if t is None:
            return None
        s = t['handle'].status()
        progreso = 0.0
        try:
            progreso = t['handle'].file_progress()[t['archivo']] / max(1, t['tamano'])
        except Exception:  # noqa: BLE001
            pass
        return {'pares': s.num_peers, 'semillas': s.num_seeds, 'bajada': s.download_payload_rate,
                'subida': s.upload_payload_rate,
                'progreso': round(progreso, 4), 'nombre': t['nombre'], 'tamano': t['tamano']}

    # ---------- cerrar (sin seguir compartiendo) ----------
    def cerrar(self, clave, guardar_en=None):
        """Quita el torrent. Con guardar_en (carpeta) y el archivo completo, lo mueve allí antes de borrar la caché."""
        with self._lock:
            t = self.activos.pop(clave, None)
        if t is None:
            return None
        h = t['handle']
        movido = None
        completo = False
        try:
            completo = h.file_progress()[t['archivo']] >= t['tamano']
        except Exception:  # noqa: BLE001
            pass
        self.ses.remove_torrent(h)
        if guardar_en and completo:
            time.sleep(0.5)
            destino = os.path.join(guardar_en, t['nombre'])
            base, ext = os.path.splitext(destino)
            n = 2
            while os.path.exists(destino):
                destino = f'{base}-{n}{ext}'
                n += 1
            try:
                shutil.move(t['ruta'], destino)
                movido = destino
            except OSError:
                movido = None
        threading.Thread(target=lambda: (time.sleep(1.0), shutil.rmtree(t['carpeta'], ignore_errors=True)),
                         daemon=True).start()
        return movido

    def cerrar_todo(self):
        for clave in list(self.activos):
            self.cerrar(clave)
        try:
            self.ses.pause()
        except Exception:  # noqa: BLE001
            pass
