"""Colecciones: grupos de enlaces y/o archivos descargados que se guardan para más tarde y se comparten.

Se guardan en %APPDATA%\\JabsDLP\\colecciones.json. "★ Favoritos" es una colección fija que no se puede borrar.
Para compartir se exportan como .jabs (JSON) o .txt (una URL por línea). Al importar todo se valida: solo
enlaces http(s), textos acotados y nada que se ejecute.
"""
import json
import os
import threading
import time
import uuid

from .ajustes import carpeta_datos

FAVORITOS = 'favoritos'
FORMATO = 'jabsdlp-coleccion'
MAX_ITEMS = 5000
MAX_COLECCIONES = 300


class ColeccionInvalida(ValueError):
    pass


def _texto(valor, maximo):
    return str(valor).strip()[:maximo] if isinstance(valor, (str, int, float)) and str(valor).strip() else None


def limpiar_item(item, permitir_rutas=True):
    """Item saneado ({url|ruta, titulo, duracion, miniatura, canal, visto, posicion}) o None si no vale."""
    if not isinstance(item, dict):
        return None
    limpio = {}
    url = item.get('url')
    ruta = item.get('ruta')
    if isinstance(url, str) and url.strip().lower().startswith(('http://', 'https://', 'magnet:?')) \
            and len(url.strip()) <= 4000 and not any(c in url.strip() for c in '\r\n\t '):
        limpio['url'] = url.strip()   # enlaces http(s) y magnets (torrents para ver o descargar)
    elif permitir_rutas and isinstance(ruta, str) and ruta.strip() and len(ruta) <= 1000 and os.path.isabs(ruta.strip()):
        limpio['ruta'] = os.path.normpath(ruta.strip())
    else:
        return None
    titulo = _texto(item.get('titulo'), 300)
    if titulo:
        limpio['titulo'] = titulo
    canal = _texto(item.get('canal'), 200)
    if canal:
        limpio['canal'] = canal
    try:
        if item.get('duracion') is not None:
            limpio['duracion'] = max(0.0, min(float(item['duracion']), 10 * 24 * 3600))
    except (TypeError, ValueError):
        pass
    mini = item.get('miniatura')
    if isinstance(mini, str) and mini.startswith('https://') and len(mini) <= 2000:
        limpio['miniatura'] = mini
    if item.get('visto') is True:
        limpio['visto'] = True
    if item.get('tipo') == 'playlist':
        limpio['tipo'] = 'playlist'
    if item.get('intentado') is True:   # ya se intentó completar su título/miniatura (no se repite)
        limpio['intentado'] = True
    try:
        if item.get('posicion'):
            limpio['posicion'] = max(0.0, float(item['posicion']))
    except (TypeError, ValueError):
        pass
    return limpio


def clave_item(item):
    return ('url', item['url']) if 'url' in item else ('ruta', os.path.normcase(item.get('ruta', '')))


class Colecciones:
    def __init__(self, ruta=None):
        self.ruta = ruta or os.path.join(carpeta_datos(), 'colecciones.json')
        self._lock = threading.RLock()
        self._datos = []
        self._cargar()

    # ---------- persistencia ----------
    def _cargar(self):
        try:
            with open(self.ruta, 'r', encoding='utf-8') as f:
                datos = json.load(f)
        except (OSError, ValueError):
            datos = []
        self._datos = []
        for c in datos if isinstance(datos, list) else []:
            if isinstance(c, dict) and isinstance(c.get('id'), str):
                items = [i for i in (limpiar_item(x) for x in (c.get('items') or [])[:MAX_ITEMS]) if i]
                self._datos.append({'id': c['id'][:24], 'nombre': _texto(c.get('nombre'), 80) or 'Colección',
                                    'creada': c.get('creada') or time.time(), 'items': items})
        if not any(c['id'] == FAVORITOS for c in self._datos):
            self._datos.insert(0, {'id': FAVORITOS, 'nombre': '★ Favoritos', 'creada': time.time(), 'items': []})
        # Favoritos siempre primero
        self._datos.sort(key=lambda c: c['id'] != FAVORITOS)

    def _guardar(self):
        temporal = self.ruta + '.tmp'
        try:
            with open(temporal, 'w', encoding='utf-8') as f:
                json.dump(self._datos, f, ensure_ascii=False)
            os.replace(temporal, self.ruta)
        except OSError:
            pass

    # ---------- consulta ----------
    def lista(self):
        with self._lock:
            return [{'id': c['id'], 'nombre': c['nombre'], 'cantidad': len(c['items']), 'fija': c['id'] == FAVORITOS,
                     'miniaturas': [i['miniatura'] for i in c['items'] if i.get('miniatura')][:3]} for c in self._datos]

    def obtener(self, id_):
        with self._lock:
            c = next((c for c in self._datos if c['id'] == id_), None)
            if c is None:
                return None
            items = []
            for i in c['items']:
                copia = dict(i)
                if 'ruta' in copia:
                    copia['existe'] = os.path.isfile(copia['ruta'])
                items.append(copia)
            return {**c, 'items': items, 'fija': c['id'] == FAVORITOS}

    def _buscar(self, id_):
        c = next((c for c in self._datos if c['id'] == id_), None)
        if c is None:
            raise ColeccionInvalida('Esa colección ya no existe.')
        return c

    # ---------- cambios ----------
    def crear(self, nombre, items=None):
        with self._lock:
            if len(self._datos) >= MAX_COLECCIONES:
                raise ColeccionInvalida('Hay demasiadas colecciones.')
            c = {'id': uuid.uuid4().hex[:10], 'nombre': _texto(nombre, 80) or 'Nueva colección', 'creada': time.time(),
                 'items': []}
            self._datos.append(c)
            if items:
                self._agregar(c, items)
            self._guardar()
            return c['id']

    def renombrar(self, id_, nombre):
        with self._lock:
            c = self._buscar(id_)
            if c['id'] == FAVORITOS:
                raise ColeccionInvalida('Favoritos no se puede renombrar.')
            c['nombre'] = _texto(nombre, 80) or c['nombre']
            self._guardar()

    def borrar(self, id_):
        with self._lock:
            if id_ == FAVORITOS:
                raise ColeccionInvalida('Favoritos no se puede borrar.')
            self._datos = [c for c in self._datos if c['id'] != id_]
            self._guardar()

    def _agregar(self, c, items):
        existentes = {clave_item(i) for i in c['items']}
        nuevos = 0
        for item in items or []:
            limpio = limpiar_item(item)
            if limpio and clave_item(limpio) not in existentes and len(c['items']) < MAX_ITEMS:
                c['items'].append(limpio)
                existentes.add(clave_item(limpio))
                nuevos += 1
        return nuevos

    def agregar(self, id_, items):
        with self._lock:
            nuevos = self._agregar(self._buscar(id_), items)
            self._guardar()
            return nuevos

    def quitar(self, id_, item):
        with self._lock:
            c = self._buscar(id_)
            limpio = limpiar_item(item)
            if limpio:
                c['items'] = [i for i in c['items'] if clave_item(i) != clave_item(limpio)]
                self._guardar()

    def reordenar(self, id_, desde, hasta):
        with self._lock:
            items = self._buscar(id_)['items']
            if 0 <= desde < len(items) and 0 <= hasta < len(items):
                items.insert(hasta, items.pop(desde))
                self._guardar()

    def progreso(self, id_, item, segundos, visto=False):
        """Guarda la posición (segundos) de un elemento; al terminar lo marca como visto y vuelve a 0."""
        limpio = limpiar_item(item)
        if not limpio:
            return
        with self._lock:
            for i in self._buscar(id_)['items']:
                if clave_item(i) == clave_item(limpio):
                    if visto:
                        i['visto'] = True
                        i.pop('posicion', None)
                    elif segundos and float(segundos) > 5:
                        i['posicion'] = round(float(segundos), 1)
                    self._guardar()
                    return

    def completar(self, id_, datos):
        """datos: {url: {titulo, miniatura, duracion, canal, tipo}}. Rellena lo que falte y marca «intentado»."""
        cambios = 0
        with self._lock:
            for i in self._buscar(id_)['items']:
                nuevo = datos.get(i.get('url'))
                if nuevo is None:
                    continue
                completo = limpiar_item({**i, **{k: v for k, v in nuevo.items() if v and not i.get(k)}, 'intentado': True})
                if completo and completo != i:
                    i.clear()
                    i.update(completo)
                    cambios += 1
            if cambios:
                self._guardar()
        return cambios

    def es_favorito(self, item):
        limpio = limpiar_item(item)
        with self._lock:
            return bool(limpio) and clave_item(limpio) in {clave_item(i) for i in self._buscar(FAVORITOS)['items']}

    def alternar_favorito(self, item):
        """Añade o quita de ★ Favoritos. Devuelve True si quedó marcado."""
        limpio = limpiar_item(item)
        if not limpio:
            raise ColeccionInvalida('Ese elemento no se puede marcar.')
        with self._lock:
            fav = self._buscar(FAVORITOS)
            if clave_item(limpio) in {clave_item(i) for i in fav['items']}:
                fav['items'] = [i for i in fav['items'] if clave_item(i) != clave_item(limpio)]
                marcado = False
            else:
                self._agregar(fav, [limpio])
                marcado = True
            self._guardar()
            return marcado

    def favoritos_rutas(self):
        with self._lock:
            return {os.path.normcase(i['ruta']) for i in self._buscar(FAVORITOS)['items'] if 'ruta' in i}

    # ---------- compartir ----------
    def exportar(self, id_, ruta, tipo='jabs', progreso=False):
        """Escribe la colección en un .jabs o .txt. Los archivos locales no se exportan (solo existen en este equipo)."""
        c = self.obtener(id_)
        if c is None:
            raise ColeccionInvalida('Esa colección ya no existe.')
        enlaces = [i for i in c['items'] if 'url' in i]
        omitidos = len(c['items']) - len(enlaces)
        if tipo == 'txt':
            contenido = '\n'.join(i['url'] for i in enlaces) + '\n'
        else:
            campos = ('url', 'titulo', 'duracion', 'canal', 'miniatura') + (('visto', 'posicion') if progreso else ())
            contenido = json.dumps({'formato': FORMATO, 'version': 1, 'nombre': c['nombre'],
                                    'items': [{k: i[k] for k in campos if k in i} for i in enlaces]},
                                   ensure_ascii=False, indent=1)
        with open(ruta, 'w', encoding='utf-8') as f:
            f.write(contenido)
        return {'exportados': len(enlaces), 'omitidos': omitidos}

    def importar(self, ruta):
        """Lee un .jabs o .txt y crea una colección nueva. Devuelve (id, cantidad)."""
        if os.path.getsize(ruta) > 20 * 1024 * 1024:
            raise ColeccionInvalida('El archivo es demasiado grande.')
        with open(ruta, 'r', encoding='utf-8', errors='replace') as f:
            texto = f.read()
        nombre = os.path.splitext(os.path.basename(ruta))[0]
        items = None
        if texto.lstrip().startswith('{'):
            try:
                datos = json.loads(texto)
            except ValueError:
                raise ColeccionInvalida('El archivo .jabs está dañado (no es JSON válido).') from None
            if not isinstance(datos, dict) or datos.get('formato') != FORMATO or not isinstance(datos.get('items'), list):
                raise ColeccionInvalida('No es una colección de JabsDLP.')
            nombre = _texto(datos.get('nombre'), 80) or nombre
            items = [limpiar_item(i, permitir_rutas=False) for i in datos['items'][:MAX_ITEMS]]
        else:
            from .utilidades import extraer_urls
            items = [{'url': u} for u in extraer_urls(texto)[:MAX_ITEMS]]
        items = [i for i in items if i]
        if not items:
            raise ColeccionInvalida('El archivo no tiene enlaces válidos.')
        id_ = self.crear(nombre, items)
        return id_, len(self.obtener(id_)['items'])
