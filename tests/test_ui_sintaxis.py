"""La interfaz no tiene compilación: un error de sintaxis en un .js (p. ej. un apóstrofo sin escapar en i18n.js)
rompería la app entera. Se comprueban todos con Node, si está instalado."""
import glob
import os
import shutil
import subprocess

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVOS = [f for f in glob.glob(os.path.join(RAIZ, 'ui', '*.js'))] + \
    glob.glob(os.path.join(RAIZ, 'android', 'app', 'src', 'main', 'assets', 'android', '*.js'))


@pytest.mark.skipif(not shutil.which('node'), reason='Node no está instalado')
@pytest.mark.parametrize('ruta', ARCHIVOS, ids=os.path.basename)
def test_js_sin_errores_de_sintaxis(ruta):
    codigo = "new Function(require('fs').readFileSync(process.argv[1], 'utf8'))"
    r = subprocess.run(['node', '-e', codigo, ruta], capture_output=True, text=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr[-800:]
