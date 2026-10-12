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
