"""Cola de descargas: en paralelo sin límite (o con límite), o de una en una."""
import json
import os
import threading

from .ajustes import carpeta_datos
from .trabajo import TERMINADOS, Trabajo, ejecutar

MAX_HISTORIAL = 300


class Gestor:
    def __init__(self, ajustes, herramientas):
        self._ajustes = ajustes
        self._herr = herramientas
        self._trabajos = {}
        self._activos = set()
        self._cv = threading.Condition()
        self._ruta_historial = os.path.join(carpeta_datos(), 'historial.json')
        self._cargar_historial()
        threading.Thread(target=self._despachar, daemon=True, name='despachador').start()

    def limite(self):
        if not self._ajustes.get('paralelo'):
            return 1
        maximo = int(self._ajustes.get('max_paralelo') or 0)
        return maximo if maximo > 0 else float('inf')

    def agregar(self, trabajos):
        with self._cv:
            for t in trabajos:
                self._trabajos[t.id] = t
            self._cv.notify_all()
        return [t.id for t in trabajos]

    def _despachar(self):
        while True:
            with self._cv:
                while True:
                    pendiente = next((t for t in self._trabajos.values() if t.estado == 'en_cola'), None)
                    if pendiente is not None and len(self._activos) < self.limite():
                        break
                    self._cv.wait(1.0)
                pendiente.estado = 'iniciando'
                self._activos.add(pendiente.id)
            threading.Thread(target=self._correr, args=(pendiente,), daemon=True).start()

    def _correr(self, trabajo):
        try:
            ejecutar(trabajo, self._ajustes, self._herr)
        finally:
            with self._cv:
                self._activos.discard(trabajo.id)
                self._cv.notify_all()
            self._guardar_historial()

    def notificar(self):
        with self._cv:
            self._cv.notify_all()

    def obtener(self, id_):
        return self._trabajos.get(id_)

    def cancelar(self, id_):
        t = self._trabajos.get(id_)
        if t is None:
            return False
        with self._cv:
            if t.estado == 'en_cola':
                t.estado = 'cancelado'
                t.fase = 'Cancelado'
            t.cancelar()
        self._guardar_historial()
        return True

    def cancelar_todo(self):
        for id_ in list(self._trabajos):
            t = self._trabajos[id_]
            if t.estado not in TERMINADOS:
                self.cancelar(id_)

    def reintentar(self, id_):
        t = self._trabajos.get(id_)
        if t is None or t.estado not in ('error', 'cancelado') or t.id in self._activos:
            return False
        with self._cv:
            t.reiniciar()
            self._cv.notify_all()
        return True

    def quitar(self, id_):
        t = self._trabajos.get(id_)
        if t is None:
            return False
        if t.estado not in TERMINADOS:
            self.cancelar(id_)
        with self._cv:
            self._trabajos.pop(id_, None)
        self._guardar_historial()
        return True

    def limpiar(self):
        with self._cv:
            for id_ in [i for i, t in self._trabajos.items() if t.estado in TERMINADOS and i not in self._activos]:
                self._trabajos.pop(id_, None)
        self._guardar_historial()

    def lista(self):
        with self._cv:
            trabajos = list(self._trabajos.values())
        return [t.a_dict() for t in trabajos]

    def resumen(self):
        with self._cv:
            estados = [t.estado for t in self._trabajos.values()]
        return {
            'activos': sum(1 for e in estados if e not in TERMINADOS and e != 'en_cola'),
            'en_cola': estados.count('en_cola'),
            'completados': estados.count('completado'),
            'errores': estados.count('error'),
            'total': len(estados),
        }

    def _cargar_historial(self):
        try:
            with open(self._ruta_historial, 'r', encoding='utf-8') as f:
                datos = json.load(f)
        except (OSError, ValueError):
            return
        for d in datos if isinstance(datos, list) else []:
            try:
                t = Trabajo.desde_dict(d)
            except (KeyError, TypeError):
                continue
            self._trabajos[t.id] = t

    def _guardar_historial(self):
        with self._cv:
            terminados = [t.a_dict() for t in self._trabajos.values() if t.estado in TERMINADOS][-MAX_HISTORIAL:]
        temporal = self._ruta_historial + '.tmp'
        try:
            with open(temporal, 'w', encoding='utf-8') as f:
                json.dump(terminados, f, ensure_ascii=False)
            os.replace(temporal, self._ruta_historial)
        except OSError:
            pass
