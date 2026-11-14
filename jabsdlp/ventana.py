"""Detalles de la ventana de Windows que pywebview no cubre: color de la barra de título y ventanas sin foco."""
import ctypes
from ctypes import wintypes

DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_CAPTION_COLOR = 35
DWMWA_TEXT_COLOR = 36


def _rgb(hex_color):
    """'#ffffff' -> COLORREF 0x00BBGGRR."""
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (b << 16) | (g << 8) | r


_set_window_pos = ctypes.WINFUNCTYPE(
    wintypes.BOOL, wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT,
    use_last_error=True)(('SetWindowPos', ctypes.windll.user32))


def hwnd_por_titulo(titulo):
    return ctypes.windll.user32.FindWindowW(None, titulo) or None


def tema_barra(hwnd, claro):
    """Barra de título clara u oscura según el tema de la app (no el de Windows). En Windows 11 también el color."""
    if not hwnd:
        return False
    dwm = ctypes.WINFUNCTYPE(ctypes.c_long, wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD)(
        ('DwmSetWindowAttribute', ctypes.windll.dwmapi))   # prototipo propio: no se pisa el que usa pywebview
    oscuro = ctypes.c_int(0 if claro else 1)
    dwm(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(oscuro), 4)
    fondo = ctypes.c_int(_rgb('#ffffff' if claro else '#09090b'))
    texto = ctypes.c_int(_rgb('#18181b' if claro else '#f4f4f5'))
    dwm(hwnd, DWMWA_CAPTION_COLOR, ctypes.byref(fondo), 4)   # en Windows 10 falla sin más
    dwm(hwnd, DWMWA_TEXT_COLOR, ctypes.byref(texto), 4)
    return True


def mostrar_sin_foco(hwnd, x, y, ancho, alto):
    """Muestra una ventana encima de todo, en píxeles físicos, sin quitar el foco a la app que estés usando."""
    if not hwnd:
        return False
    SWP_NOACTIVATE, SWP_SHOWWINDOW = 0x0010, 0x0040
    ctypes.windll.user32.ShowWindow(wintypes.HWND(hwnd), 4)   # SW_SHOWNOACTIVATE
    # HWND_TOPMOST (-1) debe ir como puntero de 64 bits: prototipo propio (sin tocar el de user32 que usa pywebview)
    _set_window_pos(hwnd, wintypes.HWND(-1), int(x), int(y), int(ancho), int(alto), SWP_NOACTIVATE | SWP_SHOWWINDOW)
    return True


def ocultar(hwnd):
    if hwnd:
        ctypes.windll.user32.ShowWindow(hwnd, 0)


def escala(hwnd):
    """Factor de escala (DPI/96) del monitor de la ventana."""
    try:
        return ctypes.windll.user32.GetDpiForWindow(hwnd) / 96.0 if hwnd else 1.0
    except (AttributeError, OSError):
        return 1.0
