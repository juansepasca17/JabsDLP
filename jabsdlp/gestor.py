"""Cola de descargas: en paralelo sin límite (o con límite), o de una en una.

También gestiona los reintentos automáticos, la pausa, el límite de velocidad total, retomar la cola al
reabrir la app y los avisos de Windows al terminar.
"""
import json
import os
import threading
import time

from .ajustes import carpeta_datos
from .trabajo import PENDIENTES, TERMINADOS, Trabajo, ejecutar
from .velocidad import Cubeta, mb_a_bytes

MAX_HISTORIAL = 300
ESPERA_BASE = 5      # segundos antes del primer reintento; luego x3 (5, 15, 45...)
ESPERA_MAX = 300


class Gestor:
    def __init__(self, ajustes, herramientas, avisar=None):
        self._ajustes = ajustes
        self._herr = herramientas
        self._avisar = avisar            # función(titulo, mensaje, archivo, carpeta) para las notificaciones
        self._trabajos = {}
        self._activos = set()
        self._grupos_avisados = set()
        self._cv = threading.Condition()
        self.pausado = False
        self.cubeta = Cubeta(lambda: mb_a_bytes(ajustes.get('limite_velocidad')))
        self._ruta_historial = os.path.join(carpeta_datos(), 'historial.json')
        self._ruta_cola = os.path.join(carpeta_datos(), 'cola.json')
        self._cargar_historial()
        if ajustes.get('retomar_cola'):
            self._cargar_cola()
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
        self._guardar_cola()
        return [t.id for t in trabajos]

    def _despachar(self):
        while True:
            with self._cv:
                while True:
                    pendiente = None if self.pausado else \
                        next((t for t in self._trabajos.values() if t.estado == 'en_cola'), None)
                    if pendiente is not None and len(self._activos) < self.limite():
                        break
                    self._cv.wait(1.0)
                pendiente.estado = 'iniciando'
                self._activos.add(pendiente.id)
                activos = len(self._activos)
            threading.Thread(target=self._correr, args=(pendiente, activos), daemon=True).start()

    def _correr(self, trabajo, activos):
        limite_aria2 = mb_a_bytes(self._ajustes.get('limite_velocidad')) // max(1, activos)
        try:
            ejecutar(trabajo, self._ajustes, self._herr, self.cubeta, limite_aria2)
        finally:
            with self._cv:
                self._activos.discard(trabajo.id)
                self._programar_reintento(trabajo)
                self._cv.notify_all()
            self._guardar_historial()
            self._guardar_cola()
            if trabajo.estado in TERMINADOS:
                self._notificar(trabajo)

    # ---------- reintentos automáticos ----------
    def _programar_reintento(self, trabajo):
        maximo = int(self._ajustes.get('reintentos') or 0)
        if trabajo.estado != 'error' or not trabajo.temporal or trabajo.intentos >= maximo:
            return
        trabajo.intentos += 1
        espera = min(ESPERA_MAX, ESPERA_BASE * 3 ** (trabajo.intentos - 1))
        if self._ajustes.get('motor') == 'auto' and trabajo.motor == 'ytdlp':
            trabajo.motor_forzado = 'aria2'   # en Auto, el reintento usa aria2
        trabajo.estado = 'reintentando'
        trabajo.reintento_en = time.time() + espera
        trabajo.fase = f'Reintento {trabajo.intentos} de {maximo}'
        temporizador = threading.Timer(espera, self._reencolar, args=(trabajo,))
        temporizador.daemon = True
        temporizador.start()

    def _reencolar(self, trabajo):
        with self._cv:
            if trabajo.estado == 'reintentando' and trabajo.id in self._trabajos:
                aviso = f'Reintento {trabajo.intentos}' + (' con aria2' if trabajo.motor_forzado == 'aria2' else '')
                trabajo.reiniciar()
                trabajo.aviso = aviso
                self._cv.notify_all()

    # ---------- avisos de Windows ----------
    def _notificar(self, trabajo):
        if not self._avisar or not self._ajustes.get('notificaciones'):
            return
        modo = self._ajustes.get('notificar_modo')
        if trabajo.grupo_id and modo == 'grupo':
            with self._cv:
                grupo = [t for t in self._trabajos.values() if t.grupo_id == trabajo.grupo_id]
                if any(t.estado not in TERMINADOS for t in grupo) or trabajo.grupo_id in self._grupos_avisados:
                    return
                self._grupos_avisados.add(trabajo.grupo_id)
            hechos = [t for t in grupo if t.estado == 'completado']
            errores = sum(1 for t in grupo if t.estado == 'error')
            if not hechos and not errores:
                return
            mensaje = f'{len(hechos)} de {len(grupo)} descargados' + (f' · {errores} con error' if errores else '')
            titulo = trabajo.subcarpeta or 'Descargas terminadas'
            archivo = next((t.archivo for t in hechos if t.archivo), None)
            self._avisar(titulo, mensaje, None, os.path.dirname(archivo) if archivo else self._ajustes.carpeta())
        elif trabajo.estado == 'completado':
            self._avisar('Descarga terminada', trabajo.titulo, trabajo.archivo,
                         os.path.dirname(trabajo.archivo) if trabajo.archivo else self._ajustes.carpeta())

    # ---------- control ----------
    def notificar(self):
        with self._cv:
            self._cv.notify_all()

    def pausar_cola(self, pausar=True):
        """Pausa: no empieza descargas nuevas (las que están en curso terminan)."""
        with self._cv:
            self.pausado = bool(pausar)
            self._cv.notify_all()
        return self.pausado

    def obtener(self, id_):
        return self._trabajos.get(id_)

    def cancelar(self, id_):
        t = self._trabajos.get(id_)
        if t is None:
            return False
        with self._cv:
            if t.estado in ('en_cola', 'reintentando', 'pausado'):
                t.estado = 'cancelado'
                t.fase = 'Cancelado'
            t.cancelar()
        self._guardar_historial()
        self._guardar_cola()
        return True

    def cancelar_todo(self):
        for id_ in list(self._trabajos):
            if self._trabajos[id_].estado not in TERMINADOS:
                self.cancelar(id_)

    def cerrar(self):
        """Al cerrar la app: con 'retomar' se guardan los pendientes y se conservan los .part; si no, se cancela."""
        if not self._ajustes.get('retomar_cola'):
            self.cancelar_todo()
            return
        self._guardar_cola()
        with self._cv:
            for t in self._trabajos.values():
                if t.estado not in TERMINADOS:
                    t.cancelar(conservar_parciales=True)

    def reintentar(self, id_):
        t = self._trabajos.get(id_)
        if t is None or t.estado not in ('error', 'cancelado', 'pausado') or t.id in self._activos:
            return False
        with self._cv:
            t.intentos = 0
            t.motor_forzado = None
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
        esperando = ('en_cola', 'reintentando', 'pausado')
        return {
            'activos': sum(1 for e in estados if e not in TERMINADOS and e not in esperando),
            'en_cola': sum(1 for e in estados if e in esperando),
            'completados': estados.count('completado'),
            'omitidos': estados.count('omitido'),
            'errores': estados.count('error'),
            'total': len(estados),
            'pausado': self.pausado,
        }

    # ---------- persistencia ----------
    def _leer(self, ruta):
        try:
            with open(ruta, 'r', encoding='utf-8') as f:
                datos = json.load(f)
            return datos if isinstance(datos, list) else []
        except (OSError, ValueError):
            return []

    def _escribir(self, ruta, datos):
        temporal = ruta + '.tmp'
        try:
            with open(temporal, 'w', encoding='utf-8') as f:
                json.dump(datos, f, ensure_ascii=False)
            os.replace(temporal, ruta)
        except OSError:
            pass

    def _cargar_historial(self):
        for d in self._leer(self._ruta_historial):
            try:
                t = Trabajo.desde_dict(d)
            except (KeyError, TypeError):
                continue
            self._trabajos[t.id] = t

    def _guardar_historial(self):
        with self._cv:
            terminados = [t.a_dict() for t in self._trabajos.values() if t.estado in TERMINADOS][-MAX_HISTORIAL:]
        self._escribir(self._ruta_historial, terminados)

    def _cargar_cola(self):
        for d in self._leer(self._ruta_cola):
            try:
                t = Trabajo.pendiente_desde_dict(d)
            except (KeyError, TypeError):
                continue
            self._trabajos[t.id] = t

    def _guardar_cola(self):
        if not self._ajustes.get('retomar_cola'):
            if os.path.exists(self._ruta_cola):
                try:
                    os.unlink(self._ruta_cola)
                except OSError:
                    pass
            return
        with self._cv:
            # Lo que cancelaste no se retoma; lo pausado al cerrar la app (pausar=True) sí
            # Los enlaces directos (.m3u8/.mpd) no se guardan: su token caduca y no debe quedar en disco
            pendientes = [t.a_dict() for t in self._trabajos.values()
                          if t.estado in PENDIENTES and (not t.cancelado or t.pausar) and not t.es_manifiesto]
        self._escribir(self._ruta_cola, pendientes)
