"""Torrents en la pestaña Ver para Android: misma interfaz que jabsdlp.ver_torrent.Torrents (la del PC), pero el
torrent lo maneja libtorrent4j desde Kotlin (com.jabsdlp.app.TorrentVer), porque el libtorrent de Python no existe
para Android. arranque.py la pone en lugar de la del PC: api.py y ver.py no cambian."""
import json
import os
import shutil
import threading
import time
import urllib.request

from jabsdlp.ver_torrent import (ESPERA_METADATOS, ESPERA_PIEZA, EXT_AUDIO, EXT_SUBS, EXT_VIDEO, VENTANA,
                                 TorrentNoReproducible, carpeta_cache)


def _nativo():
    from java import jclass
    return jclass('com.jabsdlp.app.TorrentVer')


class TorrentsAndroid:
    def __init__(self, subida_kb=20):
        self.k = _nativo()
        self.k.iniciar(max(1, int(subida_kb)))
        self.activos = {}
        self._lock = threading.Lock()

    def limite_subida(self, kb):
        self.k.limiteSubida(max(1, int(kb)))

    def abrir(self, origen):
        clave = os.urandom(6).hex()
        carpeta = os.path.join(carpeta_cache(), clave)
        os.makedirs(carpeta, exist_ok=True)
        fuente = origen
        if origen.lower().startswith(('http://', 'https://')):
            peticion = urllib.request.Request(origen, headers={'User-Agent': 'JabsDLP'})
            with urllib.request.urlopen(peticion, timeout=30) as r:
                datos = r.read(20 * 1024 * 1024 + 1)
            if len(datos) > 20 * 1024 * 1024:
                shutil.rmtree(carpeta, ignore_errors=True)
                raise TorrentNoReproducible('El archivo .torrent es demasiado grande.')
            fuente = os.path.join(carpeta, 'descargado.torrent')
            with open(fuente, 'wb') as f:
                f.write(datos)
        try:
            info = json.loads(str(self.k.metadatos(fuente, carpeta, ESPERA_METADATOS)))
        except Exception as e:  # noqa: BLE001 - torrent dañado, etc.
            shutil.rmtree(carpeta, ignore_errors=True)
            raise TorrentNoReproducible(f'No se pudo leer el torrent: {e}') from None
        if info.get('error'):
            shutil.rmtree(carpeta, ignore_errors=True)
            raise TorrentNoReproducible('No llegó la información del torrent (pocos pares o enlace caducado).')
        archivos = info['archivos']
        candidatos = [(a['tamano'], i) for i, a in enumerate(archivos) if a['ruta'].lower().endswith(EXT_VIDEO + EXT_AUDIO)]
        if not candidatos:
            shutil.rmtree(carpeta, ignore_errors=True)
            raise TorrentNoReproducible('Este torrent no tiene ningún video ni audio para reproducir.')
        _, elegido = max(candidatos)
        subs = [i for i, a in enumerate(archivos) if a['ruta'].lower().endswith(EXT_SUBS) and a['tamano'] < 2 * 1024 * 1024][:8]
        if not str(self.k.descargar(clave, carpeta, [elegido, *subs], elegido)):
            shutil.rmtree(carpeta, ignore_errors=True)
            raise TorrentNoReproducible('No se pudo empezar a descargar el torrent.')
        a = archivos[elegido]
        # Lo primero que pide el reproductor es el principio y el final del archivo (el índice de un MP4 suele ir
        # al final): se piden ya, antes de que llegue la primera petición, para que empiece antes
        pieza, primera = info['pieza'], a['inicio'] // info['pieza']
        ultima = (a['inicio'] + a['tamano'] - 1) // info['pieza']
        inicio_extra = list(range(primera, min(ultima, primera + max(1, (4 * 1024 * 1024) // pieza)) + 1))
        final_extra = list(range(max(primera, ultima - max(1, (2 * 1024 * 1024) // pieza)), ultima + 1))
        for n, p in enumerate(dict.fromkeys(inicio_extra + final_extra)):
            self.k.prioridad(clave, p, 50 + n * 60)
        with self._lock:
            self.activos[clave] = {
                'archivo': elegido, 'carpeta': carpeta, 'ruta': os.path.join(carpeta, a['ruta']),
                'nombre': os.path.basename(a['ruta']), 'tamano': a['tamano'], 'inicio': a['inicio'],
                'pieza': info['pieza'], 'piezas': info['piezas'], 'titulo': info['nombre'],
                'subs': [os.path.join(carpeta, archivos[i]['ruta']) for i in subs],
            }
        return clave

    def datos(self, clave):
        return self.activos.get(clave)

    def bloques(self, clave, inicio, fin, cancelado=lambda: False):
        """Igual que en el PC: prioriza la ventana que viene y espera cada pieza antes de leerla."""
        t = self.activos.get(clave)
        if t is None:
            return
        k, tam_pieza = self.k, t['pieza']
        posicion, avisadas = inicio, -1
        ultima_pos = t.get('ultima_pos')
        if ultima_pos is not None and abs(inicio - ultima_pos) > VENTANA:
            k.olvidarPrioridades(clave)   # un salto: fuera las prioridades viejas
        t['ultima_pos'] = inicio
        while posicion <= fin:
            pieza = (t['inicio'] + posicion) // tam_pieza
            if pieza > avisadas:
                ultima = min(t['piezas'] - 1, (t['inicio'] + min(fin, posicion + VENTANA)) // tam_pieza)
                for n, p in enumerate(range(pieza, ultima + 1)):
                    k.prioridad(clave, p, 20 + n * 100)
                avisadas = ultima
                t['ultima_pos'] = posicion
            limite = time.time() + ESPERA_PIEZA
            while not k.tienePieza(clave, pieza):
                if cancelado() or clave not in self.activos or time.time() > limite:
                    return
                time.sleep(0.05)
            hasta = min(fin, (pieza + 1) * tam_pieza - t['inicio'] - 1, t['tamano'] - 1)
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
                time.sleep(0.2)
                continue
            if posicion <= hasta:
                time.sleep(0.1)

    def estado(self, clave):
        t = self.activos.get(clave)
        if t is None:
            return None
        texto = str(self.k.estado(clave) or '')
        if not texto:
            return None
        e = json.loads(texto)
        return {'pares': e['pares'], 'semillas': e['semillas'], 'bajada': e['bajada'], 'subida': e['subida'],
                'progreso': round(e['descargado'] / max(1, t['tamano']), 4), 'nombre': t['nombre'], 'tamano': t['tamano']}

    def cerrar(self, clave, guardar_en=None):
        with self._lock:
            t = self.activos.pop(clave, None)
        if t is None:
            return None
        self.k.cerrar(clave)   # deja de compartir y borra lo descargado
        threading.Thread(target=lambda: (time.sleep(1.0), shutil.rmtree(t['carpeta'], ignore_errors=True)),
                         daemon=True).start()
        return None

    def cerrar_todo(self):
        for clave in list(self.activos):
            self.cerrar(clave)
