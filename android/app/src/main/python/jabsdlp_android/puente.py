"""Puente entre Kotlin y la Api del PC. Kotlin solo llama a las funciones de este módulo.

Cada llamada de la interfaz llega como (nombre, argumentos en JSON) y vuelve como JSON:
{"v": resultado} si fue bien o {"e": "mensaje"} si lanzó una excepción (bridge.js rechaza la promesa).
"""
import json
import threading
import traceback

from . import arranque

_api = None
_error_arranque = None
_listo = threading.Event()
_permitidas = frozenset()
_vistos = set()          # descargas terminadas ya avisadas al escáner de medios
TERMINADOS = ('completado', 'error', 'cancelado', 'omitido')   # como jabsdlp.trabajo.TERMINADOS
ESPERANDO = ('en_cola', 'reintentando', 'pausado')               # como Gestor.resumen()


def iniciar(datos, cache, descargas, nativos, funciones):
    """Arranca en segundo plano para que la ventana aparezca enseguida. `funciones`: una por línea."""
    global _permitidas
    _permitidas = frozenset(f.strip() for f in str(funciones).splitlines() if f.strip() and not f.startswith('#'))

    def tarea():
        global _api, _error_arranque
        try:
            arranque.preparar(str(datos), str(cache), str(descargas), str(nativos))
            from jabsdlp.api import Api
            _api = Api()
        except Exception:  # noqa: BLE001
            _error_arranque = traceback.format_exc()
        finally:
            _listo.set()
    threading.Thread(target=tarea, name='arranque', daemon=True).start()


def _obtener_api():
    _listo.wait()
    if _api is None:
        raise RuntimeError('JabsDLP no pudo arrancar:\n' + (_error_arranque or 'error desconocido'))
    return _api


def _a_json(valor):
    def convertir(o):
        if isinstance(o, (set, frozenset, tuple)):
            return list(o)
        if isinstance(o, bytes):
            return o.decode('utf-8', 'replace')
        return str(o)
    return json.dumps(valor, ensure_ascii=False, default=convertir)


def llamar(nombre, argumentos):
    nombre = str(nombre)
    try:
        if nombre not in _permitidas or nombre.startswith('_'):
            raise AttributeError(f'Función no disponible en Android: {nombre}')
        args = json.loads(str(argumentos) or '[]')
        if not isinstance(args, list):
            args = [args]
        resultado = getattr(_obtener_api(), nombre)(*args)
        return _a_json({'v': resultado})
    except Exception as e:  # noqa: BLE001
        return _a_json({'e': f'{type(e).__name__}: {e}'})


# ---------- servicio de descargas (notificación de progreso) ----------
def estado():
    """Resumen para la notificación del servicio y archivos nuevos para la Galería."""
    if not _listo.is_set() or _api is None:
        return _a_json({'listo': False})
    gestor = _api._gestor
    resumen = gestor.resumen()
    activos, nuevos = [], []
    for t in gestor.lista():
        if t['estado'] == 'completado' and t.get('archivo') and t['id'] not in _vistos:
            _vistos.add(t['id'])
            nuevos.append(t['archivo'])
        elif t['estado'] not in TERMINADOS and t['estado'] not in ESPERANDO:
            activos.append({'titulo': t.get('titulo') or t.get('url'), 'progreso': t.get('progreso') or 0,
                            'velocidad': t.get('velocidad'), 'estado': t['estado'],
                            'conversion': t.get('progreso_conversion') or 0})
    return _a_json({'listo': True, 'resumen': resumen, 'activos': activos, 'nuevos': nuevos})


def marcar_vistos():
    """Al abrir la app, lo que ya estaba terminado no se vuelve a escanear."""
    if _api is not None:
        for t in _api._gestor.lista():
            if t['estado'] == 'completado':
                _vistos.add(t['id'])


def detener():
    """Botón Detener de la notificación: no empieza nada nuevo y corta lo que está en curso (se puede reintentar)."""
    if _api is None:
        return
    gestor = _api._gestor
    gestor.pausar_cola(True)
    for t in gestor.lista():
        if t['estado'] not in TERMINADOS and t['estado'] not in ESPERANDO:
            gestor.cancelar(t['id'])


def cerrar():
    """La app se cierra (quitada de recientes): con «Retomar descargas» la cola se guarda para continuar al abrir."""
    if _api is not None:
        try:
            _api.cerrar()
        except Exception:  # noqa: BLE001
            pass


def ajuste(clave):
    if _api is None:
        return _a_json(None)
    return _a_json(_api._ajustes.get(str(clave)))
