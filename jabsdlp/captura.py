"""Captura rápida de enlaces mientras navegas (Ajustes → Captura rápida; todo desactivado por defecto).

- Atajo global (Ctrl+Alt+X…): copia lo que tengas seleccionado (simula Ctrl+C) y lo envía a JabsDLP. Si no había
  nada seleccionado, usa lo que ya estuviera copiado.
- Vigía del portapapeles: al copiar un enlace de un sitio que yt-dlp reconoce, lo ofrece (burbuja) o lo añade.
Solo se leen textos con http(s)://; nunca se abren ni se ejecutan.
"""
import ctypes
import re
import threading
import time
from ctypes import wintypes

from .utilidades import extraer_urls, leer_portapapeles

MODIFICADORES = {'ctrl': 0x2, 'alt': 0x1, 'shift': 0x4}
TECLAS = {'x': 0x58, 'd': 0x44, 'v': 0x56, 'w': 0x57, 'z': 0x5A}
MOD_NOREPEAT = 0x4000
WM_HOTKEY, WM_QUIT = 0x0312, 0x0012
VK_CONTROL, VK_MENU, VK_SHIFT, VK_C = 0x11, 0x12, 0x10, 0x43


def interpretar_tecla(combinacion):
    """'ctrl+alt+x' -> (modificadores, vk). ValueError si no es válida."""
    partes = (combinacion or '').lower().split('+')
    if len(partes) < 2 or partes[-1] not in TECLAS or any(p not in MODIFICADORES for p in partes[:-1]):
        raise ValueError(f'Atajo no válido: {combinacion}')
    mods = 0
    for p in partes[:-1]:
        mods |= MODIFICADORES[p]
    return mods, TECLAS[partes[-1]]


class _ENTRADA_TECLADO(ctypes.Structure):
    _fields_ = [('wVk', wintypes.WORD), ('wScan', wintypes.WORD), ('dwFlags', wintypes.DWORD),
                ('time', wintypes.DWORD), ('dwExtraInfo', ctypes.c_size_t)]


class _ENTRADA(ctypes.Structure):
    class _U(ctypes.Union):
        _fields_ = [('ki', _ENTRADA_TECLADO), ('relleno', ctypes.c_byte * 32)]
    _anonymous_ = ('u',)
    _fields_ = [('type', wintypes.DWORD), ('u', _U)]


def _teclas(*pulsaciones):
    """SendInput de una secuencia [(vk, soltar)]."""
    entradas = (_ENTRADA * len(pulsaciones))()
    for i, (vk, soltar) in enumerate(pulsaciones):
        entradas[i].type = 1  # INPUT_KEYBOARD
        entradas[i].ki = _ENTRADA_TECLADO(vk, 0, 0x2 if soltar else 0, 0, 0)
    ctypes.windll.user32.SendInput(len(pulsaciones), entradas, ctypes.sizeof(_ENTRADA))


def copiar_seleccion(espera=0.6):
    """Simula Ctrl+C en la ventana activa y devuelve el texto copiado (o lo que ya había, si no cambió)."""
    user32 = ctypes.windll.user32
    # Esperar a que se suelten las teclas del atajo (si no, la app recibiría Ctrl+Alt+C)
    limite = time.time() + 1.0
    while time.time() < limite and any(user32.GetAsyncKeyState(vk) & 0x8000 for vk in (VK_MENU, VK_SHIFT)):
        time.sleep(0.02)
    secuencia = user32.GetClipboardSequenceNumber()
    _teclas((VK_MENU, True), (VK_SHIFT, True), (VK_CONTROL, False), (VK_C, False), (VK_C, True), (VK_CONTROL, True))
    limite = time.time() + espera
    while user32.GetClipboardSequenceNumber() == secuencia and time.time() < limite:
        time.sleep(0.03)
    time.sleep(0.05)
    return leer_portapapeles()


class Atajo:
    """RegisterHotKey en un hilo propio con su bucle de mensajes."""

    def __init__(self, combinacion, al_pulsar):
        self.mods, self.vk = interpretar_tecla(combinacion)
        self._al_pulsar = al_pulsar
        self._hilo = None
        self._tid = None
        self.error = None
        self._listo = threading.Event()

    def iniciar(self):
        self._hilo = threading.Thread(target=self._bucle, daemon=True, name='atajo-captura')
        self._hilo.start()
        self._listo.wait(2)
        return self.error is None

    def _bucle(self):
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        self._tid = kernel32.GetCurrentThreadId()
        if not user32.RegisterHotKey(None, 1, self.mods | MOD_NOREPEAT, self.vk):
            self.error = 'Ese atajo ya lo usa otra aplicación; elige otro.'
            self._listo.set()
            return
        self._listo.set()
        msg = wintypes.MSG()
        try:
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == WM_HOTKEY:
                    threading.Thread(target=self._disparar, daemon=True).start()
        finally:
            user32.UnregisterHotKey(None, 1)

    def _disparar(self):
        try:
            texto = copiar_seleccion()
        except Exception:  # noqa: BLE001 - un fallo al copiar no debe tumbar el hilo del atajo
            texto = leer_portapapeles()
        urls = extraer_urls(texto)
        if urls:
            self._al_pulsar(urls, True)

    def detener(self):
        if self._tid:
            ctypes.windll.user32.PostThreadMessageW(self._tid, WM_QUIT, 0, 0)
        self._tid = None


class VigiaPortapapeles:
    """Mira el portapapeles cada 0,7 s; si se copia UN enlace de un sitio reconocido, llama a al_copiar([url])."""

    def __init__(self, al_copiar, reconocido=None):
        self._al_copiar = al_copiar
        self._reconocido = reconocido or (lambda url: True)
        self._parar = threading.Event()
        self._ultimas = {}

    def iniciar(self):
        threading.Thread(target=self._bucle, daemon=True, name='vigia-portapapeles').start()
        return True

    def _bucle(self):
        user32 = ctypes.windll.user32
        secuencia = user32.GetClipboardSequenceNumber()
        while not self._parar.wait(0.7):
            actual = user32.GetClipboardSequenceNumber()
            if actual == secuencia:
                continue
            secuencia = actual
            try:
                texto = (leer_portapapeles() or '').strip()
            except OSError:
                continue
            if not re.fullmatch(r'https?://\S{4,2000}', texto):
                continue
            ahora = time.time()
            if ahora - self._ultimas.get(texto, 0) < 10:
                continue
            self._ultimas = {u: t for u, t in self._ultimas.items() if ahora - t < 60}
            self._ultimas[texto] = ahora
            try:
                if self._reconocido(texto):
                    self._al_copiar([texto], False)
            except Exception:  # noqa: BLE001
                pass

    def detener(self):
        self._parar.set()


_cache_sitios = {}


def sitio_reconocido(url):
    """True si algún extractor de yt-dlp (que no sea el genérico) reconoce la URL. Cacheado por dominio+ruta corta."""
    from urllib.parse import urlsplit
    partes = urlsplit(url)
    clave = (partes.hostname or '') + '/' + (partes.path.split('/')[1] if partes.path.count('/') else '')
    if clave in _cache_sitios:
        return _cache_sitios[clave]
    from yt_dlp.extractor import gen_extractor_classes
    reconocido = any(ie.suitable(url) for ie in gen_extractor_classes() if ie.ie_key() not in ('Generic',))
    _cache_sitios[clave] = reconocido
    return reconocido


def pantalla_completa_activa():
    """True si hay una app a pantalla completa o en modo presentación (no se muestra la burbuja)."""
    estado = ctypes.c_int(0)
    try:
        if ctypes.windll.shell32.SHQueryUserNotificationState(ctypes.byref(estado)) != 0:
            return False
    except (AttributeError, OSError):
        return False
    return estado.value in (2, 3, 4)   # BUSY, RUNNING_D3D_FULL_SCREEN, PRESENTATION_MODE


def area_trabajo():
    """(izquierda, arriba, derecha, abajo) del área de trabajo de la pantalla principal (sin la barra de tareas)."""
    r = wintypes.RECT()
    ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(r), 0)  # SPI_GETWORKAREA
    return r.left, r.top, r.right, r.bottom
