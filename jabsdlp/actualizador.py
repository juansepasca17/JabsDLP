"""Actualiza yt-dlp sin recompilar la app.

Descarga desde PyPI la última versión del canal elegido (estable o nightly) junto con el yt-dlp-ejs que esa
versión fija, verifica el SHA-256 de ambos y los guarda en %LOCALAPPDATA%\\JabsDLP\\yt-dlp. Al arrancar,
activar() hace que `import yt_dlp` cargue esa versión si es más nueva que la incluida en el .exe; si no
importa bien, se vuelve a la incluida. Solo se guarda la última descarga.

Este módulo no debe importar yt_dlp: se usa antes de que se cargue.
"""
import hashlib
import importlib.abc
import importlib.machinery
import importlib.metadata
import json
import os
import re
import sys
import threading
import time
import urllib.request

from .ajustes import carpeta_local

PYPI = 'https://pypi.org/pypi/{paquete}/{version}json'
PAQUETES = ('yt_dlp', 'yt_dlp_ejs')
CANALES = ('estable', 'nightly')
INTERVALO_AUTO = 20 * 3600  # comprobar al abrir como mucho una vez cada 20 h

_activa = None        # versión descargada que está en uso en este proceso (o None si es la incluida)
_incluida = None      # versión empaquetada; se lee antes de activar (después los metadatos apuntan a la descargada)
_buscador = None
_tarea = {'estado': 'inactivo', 'progreso': 0.0, 'mensaje': ''}
_lock = threading.Lock()


def carpeta():
    ruta = os.path.join(carpeta_local(), 'yt-dlp')
    os.makedirs(ruta, exist_ok=True)
    return ruta


def tupla(version):
    """'2026.08.19' / '2026.9.27.232945.dev0' -> (2026, 8, 19[, 232945]) para comparar."""
    return tuple(int(p) for p in re.findall(r'\d+', str(version or ''))[:4] if p)


def es_nightly(version):
    return 'dev' in str(version or '') or len(tupla(version)) > 3


def version_incluida():
    """Versión de yt-dlp empaquetada con la app (leída de sus metadatos, sin importarla)."""
    global _incluida
    if _incluida is None:
        try:
            _incluida = importlib.metadata.version('yt-dlp')
        except importlib.metadata.PackageNotFoundError:
            _incluida = ''
    return _incluida or None


def leer_estado():
    try:
        with open(os.path.join(carpeta(), 'estado.json'), 'r', encoding='utf-8') as f:
            estado = json.load(f)
        return estado if isinstance(estado, dict) else {}
    except (OSError, ValueError):
        return {}


def guardar_estado(estado):
    ruta = os.path.join(carpeta(), 'estado.json')
    with open(ruta + '.tmp', 'w', encoding='utf-8') as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)
    os.replace(ruta + '.tmp', ruta)


def _rutas(estado):
    rutas = [os.path.join(carpeta(), a) for a in estado.get('archivos') or []]
    return rutas if rutas and all(os.path.isfile(r) for r in rutas) else None


class _Buscador(importlib.abc.MetaPathFinder):
    """Hace que yt_dlp y yt_dlp_ejs (y todos sus submódulos) se carguen desde los .whl descargados."""

    def __init__(self, rutas):
        self.rutas = rutas

    def find_spec(self, nombre, path=None, target=None):
        if nombre.split('.')[0] not in PAQUETES:
            return None
        return importlib.machinery.PathFinder.find_spec(nombre, path if '.' in nombre else self.rutas)


def activar():
    """Llamar antes de importar yt_dlp. Devuelve la versión descargada activada, o None."""
    global _activa, _buscador
    version_incluida()
    estado = leer_estado()
    version = estado.get('version')
    rutas = _rutas(estado)
    if not version or not rutas or estado.get('roto') or tupla(version) <= tupla(version_incluida()):
        return None
    _buscador = _Buscador(rutas)
    sys.meta_path.insert(0, _buscador)
    sys.path[0:0] = rutas  # para importlib.metadata y los recursos del paquete
    _activa = version
    return version


def desactivar(marcar_roto=True):
    """Vuelve a la versión incluida (si la descargada no se puede importar)."""
    global _activa, _buscador
    if _buscador in sys.meta_path:
        sys.meta_path.remove(_buscador)
    estado = leer_estado()
    sys.path[:] = [p for p in sys.path if p not in (_rutas(estado) or [])]
    for nombre in [m for m in sys.modules if m.split('.')[0] in PAQUETES]:
        del sys.modules[nombre]
    if marcar_roto and estado:
        estado['roto'] = True
        guardar_estado(estado)
    _activa, _buscador = None, None


def _json(url):
    peticion = urllib.request.Request(url, headers={'User-Agent': 'JabsDLP', 'Accept': 'application/json'})
    with urllib.request.urlopen(peticion, timeout=30) as resp:
        return json.load(resp)


def _rueda(datos):
    for archivo in datos.get('urls') or []:
        if archivo.get('packagetype') == 'bdist_wheel' and not archivo.get('yanked'):
            return archivo
    return None


def ultima_version(canal):
    """Última versión en PyPI: la estable publicada o, en nightly, la más reciente de todas."""
    datos = _json(PYPI.format(paquete='yt-dlp', version=''))
    if canal != 'nightly':
        return datos['info']['version']
    candidatas = [v for v, archivos in datos.get('releases', {}).items()
                  if any(a.get('packagetype') == 'bdist_wheel' and not a.get('yanked') for a in archivos)]
    return max(candidatas, key=tupla)


def _descargar(archivo, destino, progreso_base, peso):
    sha = hashlib.sha256()
    temporal = destino + '.parcial'
    peticion = urllib.request.Request(archivo['url'], headers={'User-Agent': 'JabsDLP'})
    with urllib.request.urlopen(peticion, timeout=60) as resp, open(temporal, 'wb') as f:
        total = int(resp.headers.get('Content-Length') or archivo.get('size') or 0)
        hecho = 0
        while bloque := resp.read(1 << 16):
            f.write(bloque)
            sha.update(bloque)
            hecho += len(bloque)
            if total:
                _tarea['progreso'] = progreso_base + peso * hecho / total
    if sha.hexdigest() != archivo['digests']['sha256']:
        os.unlink(temporal)
        raise RuntimeError(f"La suma SHA-256 de {archivo['filename']} no coincide; se descartó.")
    os.replace(temporal, destino)


def _limpiar(conservar):
    for nombre in os.listdir(carpeta()):
        if nombre.endswith(('.whl', '.parcial')) and nombre not in conservar:
            try:
                os.unlink(os.path.join(carpeta(), nombre))
            except OSError:
                pass


def restaurar():
    """Borra la versión descargada; al reiniciar se usa la incluida."""
    _limpiar(conservar=())
    estado = leer_estado()
    guardar_estado({'comprobado': estado.get('comprobado')})


def actualizar(canal='estable'):
    """Busca y descarga la última versión del canal. Pensado para ejecutarse en un hilo."""
    with _lock:
        _tarea.update(estado='buscando', progreso=0.0, mensaje='Buscando la última versión…')
        try:
            canal = canal if canal in CANALES else 'estable'
            objetivo = ultima_version(canal)
            estado = leer_estado()
            estado['comprobado'] = time.time()
            en_uso = _activa or version_incluida()
            if tupla(objetivo) <= tupla(version_incluida()):
                # La incluida ya es igual o más nueva (p. ej. al volver de nightly a estable)
                if estado.get('version'):
                    restaurar()
                    estado = leer_estado()
                    estado['comprobado'] = time.time()
                guardar_estado(estado)
                mensaje = f'Ya tienes la última versión {canal} ({version_incluida()}, incluida en la app).'
                if _activa:
                    mensaje += ' Reinicia para volver a ella.'
                _tarea.update(estado='al_dia', progreso=1.0, mensaje=mensaje)
                return _tarea
            if tupla(objetivo) == tupla(estado.get('version')) and _rutas(estado) and not estado.get('roto'):
                guardar_estado(estado)
                listo = tupla(objetivo) == tupla(en_uso)
                _tarea.update(estado='al_dia' if listo else 'listo', progreso=1.0,
                              mensaje=f'yt-dlp {objetivo} ya está descargado' + ('.' if listo else '; reinicia para usarlo.'))
                return _tarea

            _tarea.update(estado='descargando', mensaje=f'Descargando yt-dlp {objetivo}…')
            datos = _json(PYPI.format(paquete='yt-dlp', version=f'{objetivo}/'))
            rueda = _rueda(datos)
            if not rueda:
                raise RuntimeError(f'yt-dlp {objetivo} no tiene paquete descargable.')
            fijado = next((m.group(1) for r in datos['info'].get('requires_dist') or []
                           if (m := re.match(r'yt-dlp-ejs\s*==\s*([\w.]+)', r))), None)
            archivos = [(rueda, 0.0, 0.85)]
            if fijado:
                datos_ejs = _json(PYPI.format(paquete='yt-dlp-ejs', version=f'{fijado}/'))
                rueda_ejs = _rueda(datos_ejs)
                if not rueda_ejs:
                    raise RuntimeError(f'yt-dlp-ejs {fijado} no tiene paquete descargable.')
                archivos.append((rueda_ejs, 0.85, 0.15))
            for archivo, base, peso in archivos:
                _descargar(archivo, os.path.join(carpeta(), archivo['filename']), base, peso)

            nombres = [a['filename'] for a, _, _ in archivos]
            guardar_estado({'version': objetivo, 'canal': canal, 'ejs': fijado, 'archivos': nombres,
                            'fecha': time.time(), 'comprobado': time.time()})
            _limpiar(conservar=nombres)
            _tarea.update(estado='listo', progreso=1.0, mensaje=f'yt-dlp {objetivo} descargado; reinicia para usarlo.')
        except Exception as e:  # noqa: BLE001 - se muestra en Ajustes
            _tarea.update(estado='error', progreso=0.0, mensaje=f'No se pudo actualizar yt-dlp: {e}')
        return dict(_tarea)


def actualizar_en_segundo_plano(canal):
    if _tarea['estado'] in ('buscando', 'descargando'):
        return dict(_tarea)
    _tarea.update(estado='buscando', progreso=0.0, mensaje='Buscando la última versión…')
    threading.Thread(target=actualizar, args=(canal,), daemon=True).start()
    return dict(_tarea)


def toca_comprobar():
    return time.time() - (leer_estado().get('comprobado') or 0) > INTERVALO_AUTO


def estado_publico(en_uso):
    estado = leer_estado()
    descargada = estado.get('version') if _rutas(estado) else None
    activable = bool(descargada and not estado.get('roto') and tupla(descargada) > tupla(version_incluida()))
    return {
        'en_uso': en_uso,
        'actualizada': _activa is not None,
        'nightly': es_nightly(en_uso),
        'incluida': version_incluida(),
        'descargada': descargada,
        'roto': bool(estado.get('roto')),
        'reiniciar': (activable and tupla(descargada) != tupla(en_uso)) or (not activable and _activa is not None),
        'tarea': dict(_tarea),
    }
