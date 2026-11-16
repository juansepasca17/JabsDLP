"""Log propio de JabsDLP (Ajustes → Avanzado → «Guardar log de la app», activado por defecto).

Unas pocas líneas por acción: qué se abre en Ver (y cuánto tarda), torrents (pares, velocidad), descargas (inicio,
fin, tamaño, errores con detalle) y errores de la interfaz. Sirve para mandarlo si algo falla.
- Cada vez que se abre la app empieza un log nuevo; solo se guarda la sesión anterior (por si se cerró de golpe).
- Tamaño limitado (se recorta solo) y las URLs con tokens se ocultan.
- Con el ajuste apagado no se escribe nada.
"""
import logging
import logging.handlers
import os
import threading

from .ajustes import carpeta_local

MAX_BYTES = 1_500_000
_registro = logging.getLogger('jabsdlp.app')
_registro.propagate = False
_registro.setLevel(logging.INFO)
_manejador = None
_lock = threading.Lock()


def carpeta():
    ruta = os.path.join(carpeta_local(), 'logs')
    os.makedirs(ruta, exist_ok=True)
    return ruta


def ruta_actual():
    return os.path.join(carpeta(), 'jabsdlp.log')


def ruta_anterior():
    return os.path.join(carpeta(), 'jabsdlp-anterior.log')


class _SinTokens(logging.Formatter):
    def format(self, registro):
        from .utilidades import ocultar_tokens
        return ocultar_tokens(super().format(registro))


def iniciar(activo=True):
    """Al abrir la app: la sesión anterior pasa a jabsdlp-anterior.log y empieza una nueva."""
    with _lock:
        _cerrar_manejador()
        try:
            if os.path.isfile(ruta_actual()):
                os.replace(ruta_actual(), ruta_anterior())
            for viejo in (ruta_actual() + '.1',):
                if os.path.isfile(viejo):
                    os.unlink(viejo)
        except OSError:
            pass
    activar(activo)


def activar(activo):
    global _manejador
    with _lock:
        if not activo:
            _cerrar_manejador()
            return
        if _manejador is not None:
            return
        try:
            _manejador = logging.handlers.RotatingFileHandler(ruta_actual(), maxBytes=MAX_BYTES, backupCount=1,
                                                              encoding='utf-8', delay=True)
        except OSError:
            _manejador = None
            return
        _manejador.setFormatter(_SinTokens('%(asctime)s %(levelname)-5s %(message)s', '%Y-%m-%d %H:%M:%S'))
        _registro.addHandler(_manejador)


def _cerrar_manejador():
    global _manejador
    if _manejador is not None:
        _registro.removeHandler(_manejador)
        try:
            _manejador.close()
        except OSError:
            pass
        _manejador = None


def info(mensaje, *args):
    if _manejador is not None:
        try:
            _registro.info(mensaje, *args)
        except Exception:  # noqa: BLE001 - el log nunca debe romper la app
            pass


def error(mensaje, *args, detalle=None):
    if _manejador is not None:
        try:
            _registro.error(mensaje + (f'\n{detalle.rstrip()}' if detalle else ''), *args)
        except Exception:  # noqa: BLE001
            pass


def texto():
    """Sesión anterior + actual (lo que se exporta)."""
    partes = []
    for titulo, ruta in (('Sesión anterior', ruta_anterior()), ('Sesión actual', ruta_actual() + '.1'),
                         ('Sesión actual', ruta_actual())):
        try:
            with open(ruta, encoding='utf-8', errors='replace') as f:
                contenido = f.read().strip()
        except OSError:
            continue
        if contenido:
            partes.append(f'===== {titulo} =====\n{contenido}')
    return '\n\n'.join(partes)


def borrar():
    with _lock:
        activo = _manejador is not None
        _cerrar_manejador()
        for ruta in (ruta_actual(), ruta_actual() + '.1', ruta_anterior()):
            try:
                os.unlink(ruta)
            except OSError:
                pass
    activar(activo)
