"""Límite de velocidad TOTAL compartido por todas las descargas (cubeta de fichas).

yt-dlp aplica su 'ratelimit' por cada hilo de fragmentos y lo copia al empezar, así que no sirve para un límite
global que se pueda cambiar en caliente. En su lugar, el gancho de progreso de cada descarga llama a consumir()
con los bytes nuevos y, si se va por encima del límite, ese hilo espera lo justo.
"""
import threading
import time


class Cubeta:
    def __init__(self, limite_bytes):
        self._limite = limite_bytes          # función que devuelve bytes/s (0 o None = sin límite)
        self._lock = threading.Lock()
        self._fichas = 0.0
        self._ultimo = time.monotonic()
        self._vistos = {}                    # clave de archivo -> bytes ya contados

    def bytes_nuevos(self, clave, descargados):
        """Convierte el contador acumulado de un archivo en bytes nuevos desde la última vez."""
        with self._lock:
            anterior = self._vistos.get(clave, 0)
            nuevos = descargados - anterior if descargados >= anterior else descargados
            self._vistos[clave] = descargados
            return max(0, nuevos)

    def olvidar(self, clave):
        with self._lock:
            self._vistos.pop(clave, None)

    def consumir(self, cantidad):
        limite = self._limite() or 0
        if limite <= 0 or cantidad <= 0:
            return 0.0
        with self._lock:
            ahora = time.monotonic()
            # Se permite una ráfaga de como mucho medio segundo para que no vaya a tirones
            self._fichas = min(limite * 0.5, self._fichas + (ahora - self._ultimo) * limite)
            self._ultimo = ahora
            self._fichas -= cantidad
            espera = -self._fichas / limite if self._fichas < 0 else 0.0
        if espera > 0:
            time.sleep(min(espera, 5.0))
        return espera


def mb_a_bytes(mb):
    try:
        return int(float(mb or 0) * 1024 * 1024)
    except (TypeError, ValueError):
        return 0
