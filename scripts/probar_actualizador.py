"""Prueba el actualizador de yt-dlp sin usar la interfaz (necesita red).

1) Con LOCALAPPDATA redirigido a una carpeta temporal, descarga la última nightly.
2) En un subproceso nuevo (mismo LOCALAPPDATA), llama a activar(), importa yt_dlp y
   comprueba que el módulo sale de los .whl descargados y no de la versión incluida.

Uso:  .venv\\Scripts\\python.exe scripts\\probar_actualizador.py
"""
import json
import os
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _importar_actualizador():
    if RAIZ not in sys.path:
        sys.path.insert(0, RAIZ)
    from jabsdlp import actualizador
    return actualizador


def en_subproceso():
    """Fase 2 (proceso nuevo): activar() + import yt_dlp."""
    actualizador = _importar_actualizador()
    version = actualizador.activar()
    print('activar() ->', version)
    import yt_dlp
    print('yt_dlp.__file__ =', yt_dlp.__file__)
    print('yt_dlp.version.__version__ =', yt_dlp.version.__version__)
    ok = bool(version) and '.whl' in (yt_dlp.__file__ or '')
    print('VEREDICTO:', 'ok, se usa la versión descargada' if ok else 'FALLA, no se usa la descargada')
    return 0 if ok else 1


def principal():
    base = tempfile.mkdtemp(prefix='jabsdlp-actualizador-')
    os.environ['LOCALAPPDATA'] = base
    print('LOCALAPPDATA =', base)
    actualizador = _importar_actualizador()
    print("actualizar('nightly') ->", json.dumps(actualizador.actualizar('nightly'), ensure_ascii=False))
    carpeta = actualizador.carpeta()
    for nombre in sorted(os.listdir(carpeta)):
        print(' -', nombre)
    print('estado.json:', json.dumps(actualizador.leer_estado(), ensure_ascii=False, indent=2))
    comando = [sys.executable, os.path.abspath(__file__), '--activar']
    return subprocess.run(comando, cwd=RAIZ, env=dict(os.environ), check=False).returncode


if __name__ == '__main__':
    sys.exit(en_subproceso() if '--activar' in sys.argv else principal())
