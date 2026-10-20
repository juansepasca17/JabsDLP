"""Que ningún proceso hijo (ffmpeg, aria2, PowerShell...) siga vivo si JabsDLP se cierra o se cuelga.

Se mete el propio proceso en un "Job Object" de Windows con JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE: cuando la app
termina (aunque sea de golpe), Windows cierra el job y mata a todos sus hijos. El reinicio de la app se lanza
con CREATE_BREAKAWAY_FROM_JOB para que la nueva instancia no muera con la anterior.
"""
import ctypes
import os
from ctypes import wintypes

CREATE_BREAKAWAY_FROM_JOB = 0x01000000
_job = None


class _LIMITES_BASICOS(ctypes.Structure):
    _fields_ = [('PerProcessUserTimeLimit', ctypes.c_int64), ('PerJobUserTimeLimit', ctypes.c_int64),
                ('LimitFlags', wintypes.DWORD), ('MinimumWorkingSetSize', ctypes.c_size_t),
                ('MaximumWorkingSetSize', ctypes.c_size_t), ('ActiveProcessLimit', wintypes.DWORD),
                ('Affinity', ctypes.c_size_t), ('PriorityClass', wintypes.DWORD), ('SchedulingClass', wintypes.DWORD)]


class _IO(ctypes.Structure):
    _fields_ = [(n, ctypes.c_uint64) for n in ('Read', 'Write', 'Other', 'ReadT', 'WriteT', 'OtherT')]


class _LIMITES_EXTENDIDOS(ctypes.Structure):
    _fields_ = [('BasicLimitInformation', _LIMITES_BASICOS), ('IoInfo', _IO),
                ('ProcessMemoryLimit', ctypes.c_size_t), ('JobMemoryLimit', ctypes.c_size_t),
                ('PeakProcessMemoryUsed', ctypes.c_size_t), ('PeakJobMemoryUsed', ctypes.c_size_t)]


def proteger():
    """Llamar una vez al arrancar. Si Windows no lo permite, la app sigue igual."""
    global _job
    if os.name != 'nt' or _job is not None:
        return False
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        return False
    info = _LIMITES_EXTENDIDOS()
    # KILL_ON_JOB_CLOSE (0x2000) + BREAKAWAY_OK (0x800): los hijos mueren con la app, salvo el reinicio
    info.BasicLimitInformation.LimitFlags = 0x2000 | 0x800
    ok = kernel32.SetInformationJobObject(wintypes.HANDLE(job), 9, ctypes.byref(info), ctypes.sizeof(info))
    if ok and kernel32.AssignProcessToJobObject(wintypes.HANDLE(job), wintypes.HANDLE(kernel32.GetCurrentProcess())):
        _job = job  # se mantiene abierto mientras viva el proceso
        return True
    kernel32.CloseHandle(wintypes.HANDLE(job))
    return False


# ---------- una sola instancia ----------
MUTEX = r'Local\JabsDLP-instancia'
EVENTO = r'Local\JabsDLP-mostrar'
_mutex = None


def instancia_unica(esperar=0.0):
    """True si esta es la única instancia. Con `esperar` (reinicio) se reintenta mientras la anterior se cierra."""
    global _mutex
    if os.name != 'nt':
        return True
    import time
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    limite = time.monotonic() + esperar
    while True:
        mutex = kernel32.CreateMutexW(None, False, MUTEX)
        if mutex and ctypes.get_last_error() != 183:   # ERROR_ALREADY_EXISTS
            _mutex = mutex   # se mantiene abierto mientras viva el proceso
            return True
        if mutex:
            kernel32.CloseHandle(wintypes.HANDLE(mutex))
        if not mutex or time.monotonic() >= limite:
            return not mutex   # si Windows no deja crear el mutex, no se bloquea el arranque
        time.sleep(0.25)


def avisar_instancia_abierta():
    """Pide a la instancia que ya está abierta que muestre su ventana."""
    if os.name != 'nt':
        return False
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel32.OpenEventW.restype = wintypes.HANDLE
    evento = kernel32.OpenEventW(0x0002, False, EVENTO)   # EVENT_MODIFY_STATE
    if not evento:
        return False
    kernel32.SetEvent(wintypes.HANDLE(evento))
    kernel32.CloseHandle(wintypes.HANDLE(evento))
    return True


def escuchar_mostrar(funcion):
    """En un hilo: cada vez que otra instancia se abre, llama a `funcion` (mostrar la ventana)."""
    if os.name != 'nt':
        return
    import threading
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel32.CreateEventW.restype = wintypes.HANDLE
    evento = kernel32.CreateEventW(None, False, False, EVENTO)   # auto-reset
    if not evento:
        return

    def bucle():
        while kernel32.WaitForSingleObject(wintypes.HANDLE(evento), 0xFFFFFFFF) == 0:
            try:
                funcion()
            except Exception:  # noqa: BLE001 - la ventana pudo cerrarse
                pass
    threading.Thread(target=bucle, daemon=True, name='otra-instancia').start()
