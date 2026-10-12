"""Icono en la bandeja del sistema: al minimizar, la ventana se oculta y las descargas siguen.

Menú: Mostrar, Pausar/Reanudar la cola, Abrir carpeta, Salir. La X de la ventana sigue cerrando la app.
"""
import threading

import pystray
from PIL import Image


class Bandeja:
    def __init__(self, ruta_icono, mostrar, pausar, abrir_carpeta, salir, estado, textos):
        self._mostrar = mostrar
        self._pausar = pausar            # función(pausar: bool) -> bool
        self._abrir_carpeta = abrir_carpeta
        self._salir = salir
        self._estado = estado            # función() -> (activas, pausado)
        self._textos = textos            # función() -> dict con los textos del idioma actual
        self._icono = None
        self._imagen = Image.open(ruta_icono)
        self._hilo = None
        self._parar = threading.Event()

    def _menu(self):
        t = self._textos()
        return pystray.Menu(
            pystray.MenuItem(t['mostrar'], lambda: self._accion(self._mostrar), default=True),
            pystray.MenuItem(lambda _: t['reanudar'] if self._estado()[1] else t['pausar'],
                             lambda: self._pausar(not self._estado()[1])),
            pystray.MenuItem(t['carpeta'], lambda: self._abrir_carpeta()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(t['salir'], lambda: self._accion(self._salir)),
        )

    def _accion(self, funcion):
        self.ocultar()
        funcion()

    def _titulo(self):
        activas, pausado = self._estado()
        t = self._textos()
        if pausado:
            return f"JabsDLP · {t['en_pausa']}"
        return f"JabsDLP · {t['activas'].format(n=activas)}" if activas else 'JabsDLP'

    def mostrar_icono(self):
        if self._icono is not None:
            return
        self._icono = pystray.Icon('JabsDLP', self._imagen, self._titulo(), self._menu())
        self._icono.run_detached()
        self._parar.clear()
        self._hilo = threading.Thread(target=self._actualizar, daemon=True)
        self._hilo.start()

    def _actualizar(self):
        while not self._parar.wait(2.0):
            icono = self._icono
            if icono is None:
                return
            try:
                icono.title = self._titulo()
            except Exception:  # noqa: BLE001 - el icono pudo cerrarse entre medias
                return

    def ocultar(self):
        self._parar.set()
        icono, self._icono = self._icono, None
        if icono is not None:
            try:
                icono.stop()
            except Exception:  # noqa: BLE001
                pass
