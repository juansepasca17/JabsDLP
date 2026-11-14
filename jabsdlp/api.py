"""Puente entre la interfaz (JavaScript) y el motor. pywebview expone los métodos públicos."""
import json
import locale
import os
import time
import shutil
import subprocess
import sys
import threading
import uuid

import yt_dlp
from yt_dlp.utils import sanitize_filename

from . import APP_NAME, VERSION, actualizador, aria2, biblioteca, captura, notificar, sponsor, ventana
from .ajustes import Ajustes, carpeta_datos, carpeta_local
from .argumentos import ArgumentosInvalidos, interpretar
from .colecciones import ColeccionInvalida, Colecciones
from .cookies import limpiar_temporales_huerfanos
from .analizador import Analizador
from .ffmpeg_tools import Herramientas
from .formatos import NOMBRE_CRITERIO, calcular, normalizar
from .gestor import Gestor
from .impersonacion import impersonation_disponible
from .trabajo import TERMINADOS, Trabajo, ruta_archivo_descargados
from .utilidades import (abrir_en_explorador, error_amigable, es_manifiesto, es_medio, es_torrent, extraer_urls,
                         leer_portapapeles, leer_urls_txt, nombre_manifiesto, nombre_torrent, referer_desde, runtimes_js)


def _ok(**datos):
    return {'ok': True, **datos}


def _fallo(e):
    return {'ok': False, 'error': error_amigable(e)}


TEXTOS = {
    'es': {'mostrar': 'Mostrar JabsDLP', 'pausar': 'Pausar la cola', 'reanudar': 'Reanudar la cola',
           'carpeta': 'Abrir carpeta de descargas', 'salir': 'Salir', 'en_pausa': 'cola en pausa',
           'activas': '{n} descargas activas', 'abrir_carpeta': 'Abrir carpeta', 'abrir_archivo': 'Abrir archivo',
           'terminada': 'Descarga terminada', 'terminadas': 'Descargas terminadas'},
    'en': {'mostrar': 'Show JabsDLP', 'pausar': 'Pause queue', 'reanudar': 'Resume queue',
           'carpeta': 'Open downloads folder', 'salir': 'Quit', 'en_pausa': 'queue paused',
           'activas': '{n} active downloads', 'abrir_carpeta': 'Open folder', 'abrir_archivo': 'Open file',
           'terminada': 'Download finished', 'terminadas': 'Downloads finished'},
}


def _segundos(valor):
    """'1:20' / '01:02:03' / '80' -> segundos; None si no es válido."""
    try:
        partes = [float(p) for p in str(valor).strip().split(':')]
    except ValueError:
        return None
    if not partes or len(partes) > 3 or any(p < 0 for p in partes):
        return None
    total = 0.0
    for p in partes:
        total = total * 60 + p
    return total


class Api:
    def __init__(self):
        limpiar_temporales_huerfanos()
        self._ajustes = Ajustes()
        self._herr = Herramientas(self._ajustes)
        self._analizador = Analizador(self._ajustes)
        self._icono_avisos = self._copiar_icono()
        self._gestor = Gestor(self._ajustes, self._herr, avisar=self._avisar)
        self._ventana = None
        self._burbuja = None            # ventana pequeña para sugerir enlaces copiados (la crea main.py)
        self._colecciones = Colecciones()
        self._atajo = None
        self._vigia = None
        self._sugerida = None           # URL mostrada en la burbuja
        self._temporizador_burbuja = None
        threading.Thread(target=self._herr.detectar_gpu, daemon=True).start()
        if self._ajustes.get('ytdlp_auto') and actualizador.toca_comprobar():
            actualizador.actualizar_en_segundo_plano(self._ajustes.get('ytdlp_canal'))

    def idioma(self):
        elegido = self._ajustes.get('idioma')
        if elegido in TEXTOS:
            return elegido
        sistema = (locale.getlocale()[0] or os.environ.get('LANG') or 'es').lower()
        return 'es' if sistema.startswith(('es', 'spanish')) else 'en'

    def textos(self):
        return TEXTOS[self.idioma()]

    @staticmethod
    def _copiar_icono():
        """Las notificaciones necesitan una ruta fija al icono (la del .exe es temporal)."""
        base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        origen = os.path.join(base, 'assets', 'icono.png')
        destino = os.path.join(carpeta_local(), 'icono.png')
        try:
            if os.path.isfile(origen) and (not os.path.isfile(destino)
                                           or os.path.getsize(destino) != os.path.getsize(origen)):
                shutil.copyfile(origen, destino)
        except OSError:
            return None
        return destino if os.path.isfile(destino) else None

    def _avisar(self, titulo, mensaje, archivo, carpeta):
        t = self.textos()
        titulo = {'Descarga terminada': t['terminada'], 'Descargas terminadas': t['terminadas']}.get(titulo, titulo)
        notificar.mostrar(titulo, mensaje, archivo, carpeta, self._icono_avisos,
                          {'carpeta': t['abrir_carpeta'], 'archivo': t['abrir_archivo']})

    def _ya_descargados(self):
        if not self._ajustes.get('no_repetir'):
            return set()
        try:
            with open(ruta_archivo_descargados(), 'r', encoding='utf-8') as f:
                return {linea.strip() for linea in f if linea.strip()}  # los ID distinguen mayúsculas
        except OSError:
            return set()

    def _dialogo(self, tipo, **kwargs):
        import webview
        if self._ventana is None:
            return None
        try:
            resultado = self._ventana.create_file_dialog(getattr(webview.FileDialog, tipo), **kwargs)
        except Exception:  # noqa: BLE001 - un diálogo que falla no debe dejar el botón sin respuesta
            return None
        if not resultado:
            return None
        return resultado[0] if isinstance(resultado, (list, tuple)) else resultado

    # ---------- arranque / estado ----------
    def iniciar(self):
        return _ok(
            app=APP_NAME,
            version=VERSION,
            ytdlp=yt_dlp.version.__version__,
            ajustes=self._ajustes.todo(),
            herramientas=self.herramientas(),
        )

    def herramientas(self):
        estado = self._herr.estado()
        estado['encoder'] = self._herr.descripcion_encoder() if estado['gpu'] is not None else None
        estado['js'] = sorted(runtimes_js())
        estado['ytdlp'] = actualizador.estado_publico(yt_dlp.version.__version__)
        disponible, motivo = impersonation_disponible()
        estado['impersonacion'] = {'disponible': disponible, 'motivo': motivo,
                                   'activo': bool(self._ajustes.get('impersonar'))}
        estado['aria2'] = {'ruta': aria2.ruta(self._ajustes), 'version': aria2.VERSION, 'descarga': dict(aria2.descarga),
                           'de_la_app': aria2.instalado_por_la_app()}
        return estado

    def descargar_aria2(self):
        return aria2.descargar()

    def desinstalar_aria2(self):
        if any(t['motor'] == 'aria2' and t['estado'] not in TERMINADOS for t in self._gestor.lista()):
            return {'ok': False, 'error': 'Hay descargas usando aria2: espera a que terminen o cancélalas.'}
        try:
            aria2.desinstalar()
        except OSError as e:
            return {'ok': False, 'error': f'No se pudo borrar aria2: {e}'}
        cambios = {'aria2_ruta': ''}
        if self._ajustes.get('motor') != 'ytdlp':
            cambios['motor'] = 'ytdlp'
        self.guardar_ajustes(cambios)
        otro = aria2.ruta(self._ajustes)
        return {'ok': True, 'ajustes': self._ajustes.todo(), 'otro': otro}

    def detectar_gpu(self):
        self._herr.detectar_gpu(forzar=True)
        return self.herramientas()

    def descargar_ffmpeg(self):
        return self._herr.descargar_ffmpeg()

    # ---------- yt-dlp ----------
    def buscar_ytdlp(self):
        actualizador.actualizar_en_segundo_plano(self._ajustes.get('ytdlp_canal'))
        return self.herramientas()

    def restaurar_ytdlp(self):
        actualizador.restaurar()
        return self.herramientas()

    def reiniciar(self):
        resumen = self._gestor.resumen()
        if resumen['activos'] or resumen['en_cola']:
            return {'ok': False, 'error': 'Hay descargas en curso: espera a que terminen o cancélalas antes de reiniciar.'}
        comando = [sys.executable] if getattr(sys, 'frozen', False) else [sys.executable, os.path.abspath(sys.argv[0])]
        # nueva instancia independiente del .exe; espera a que esta se cierre (instancia única)
        entorno = dict(os.environ, PYINSTALLER_RESET_ENVIRONMENT='1', JABSDLP_REINICIO='1')
        from .procesos import CREATE_BREAKAWAY_FROM_JOB
        subprocess.Popen(comando, env=entorno, close_fds=True, creationflags=CREATE_BREAKAWAY_FROM_JOB)
        if self._ventana is not None:
            threading.Timer(0.4, self._ventana.destroy).start()
        return {'ok': True}

    # ---------- analizar ----------
    def analizar(self, url, modo='auto', prefs=None, origen=None):
        url = (url or '').strip()
        if es_torrent(url):
            return _ok(datos={'tipo': 'torrent', 'id': None, 'url': url, 'titulo': nombre_torrent(url),
                              'riesgos': ['torrent'], 'aria2': bool(aria2.ruta(self._ajustes))})
        urls = extraer_urls(url)
        if len(urls) > 1:
            return _ok(datos={'tipo': 'lote', 'id': None, 'urls': urls, 'cantidad': len(urls)})
        if not urls:
            return {'ok': False, 'error': 'Pega una URL válida (debe empezar por http).'}
        if es_manifiesto(urls[0]):
            # Enlace directo .m3u8/.mpd: comprobación previa con Referer (nunca bloquea la descarga)
            try:
                return _ok(datos=self._analizador.analizar_manifiesto(urls[0], origen))
            except Exception as e:  # noqa: BLE001
                return _fallo(e)
        try:
            datos = self._analizador.analizar(urls[0], modo)
            vistos = self._ya_descargados()
            if datos['tipo'] == 'video':
                datos.update(self.opciones(datos['id'], prefs or self._ajustes.get('prefs')))
                datos['ya_descargado'] = f"{(datos.get('sitio_clave') or '').lower()} {datos.get('video_id')}" in vistos
            else:
                for e in datos['entradas']:
                    e['ya_descargado'] = f"{(e.get('sitio_clave') or '').lower()} {e.get('video_id')}" in vistos
            return _ok(datos=datos)
        except Exception as e:  # noqa: BLE001
            return _fallo(e)

    def opciones(self, id_, prefs, audio_id=None):
        datos = self._analizador.obtener(id_)
        if not datos or '_info' not in datos:
            return {'recomendado': None, 'opciones': [], 'audios': [], 'audio_elegido': None}
        resultado = calcular(datos['_info'], prefs or {}, audio_id)
        resultado['encoder'] = self._herr.descripcion_encoder() if self._herr.estado()['gpu'] is not None else None
        return resultado

    # ---------- descargar ----------
    def descargar(self, solicitud):
        try:
            prefs = normalizar(solicitud.get('prefs') or self._ajustes.get('prefs'))
            if solicitud.get('tipo') not in ('torrent', 'manifiesto', 'stack'):
                self._ajustes.actualizar({'prefs': prefs})
            auto = f"Auto · {NOMBRE_CRITERIO[prefs['criterio']]}"
            tipo = solicitud.get('tipo')
            trabajos = []
            if tipo == 'video':
                datos = self._analizador.obtener(solicitud.get('id'))
                if not datos:
                    return {'ok': False, 'error': 'El análisis caducó; vuelve a analizar la URL.'}
                calculo = calcular(datos['_info'], prefs, solicitud.get('audio_id'))
                todas = ([calculo['recomendado']] if calculo['recomendado'] else []) + calculo['opciones']
                spec = solicitud.get('spec')
                elegida = next((o for o in todas if o['spec'] == spec), None) if spec else calculo['recomendado']
                recorte = self._validar_recorte(solicitud.get('recorte'), datos.get('duracion'))
                tamano = elegida.get('tamano') if elegida else None
                if recorte and tamano and datos.get('duracion'):
                    tamano = int(tamano * (recorte[1] - recorte[0]) / datos['duracion'])
                trabajos.append(Trabajo(
                    datos['url'], prefs, datos['titulo'], datos['miniatura'], datos['canal'], datos['duracion'],
                    formato=elegida['spec'] if elegida else None,
                    contenedor=elegida.get('contenedor') if elegida and prefs.get('tipo') != 'audio' else None,
                    titulo_formato=elegida['titulo'] if elegida else 'Auto',
                    tamano=tamano, recorte=recorte, quitar_anuncios=bool(solicitud.get('quitar_anuncios')),
                ))
            elif tipo == 'playlist':
                datos = self._analizador.obtener(solicitud.get('id'))
                if not datos:
                    return {'ok': False, 'error': 'El análisis caducó; vuelve a analizar la URL.'}
                elegidos = set(solicitud.get('indices') or [e['indice'] for e in datos['entradas']])
                grupo = uuid.uuid4().hex[:12]
                total = len(datos['entradas'])
                for e in datos['entradas']:
                    if e['indice'] in elegidos:
                        trabajos.append(Trabajo(e['url'], prefs, e['titulo'], e['miniatura'], e['canal'] or datos['canal'],
                                                e['duracion'], titulo_formato=auto, subcarpeta=datos['titulo'],
                                                grupo_id=grupo, indice=e['indice'], total_grupo=total,
                                                quitar_anuncios=bool(solicitud.get('quitar_anuncios'))))
            elif tipo == 'torrent':
                url = (solicitud.get('url') or '').strip()
                if not es_torrent(url):
                    return {'ok': False, 'error': 'No es un enlace magnet ni un archivo .torrent.'}
                if not aria2.ruta(self._ajustes):
                    return {'ok': False, 'error': 'Los torrents necesitan aria2: instálalo en Ajustes → Red y velocidad.'}
                trabajos.append(Trabajo(url, {'tipo': 'torrent'}, nombre_torrent(url), titulo_formato='Torrent · sin seed'))
            elif tipo == 'manifiesto':
                url = (solicitud.get('url') or '').strip()
                ext = es_manifiesto(url)
                if not ext:
                    return {'ok': False, 'error': 'No es un enlace .m3u8 ni .mpd.'}
                # Va como cabecera HTTP: sin saltos de línea (inyección de cabeceras) y con longitud acotada
                referer = ''.join(str(solicitud.get('referer') or '').split())[:500] or referer_desde(url)
                if referer and not referer.lower().startswith(('http://', 'https://')):
                    referer = 'https://' + referer
                nombre = nombre_manifiesto((solicitud.get('nombre') or '').strip() or url)
                trabajos.append(Trabajo(url, {'tipo': 'manifiesto', 'referer': referer, 'nombre': nombre}, nombre,
                                        titulo_formato=f'Enlace directo .{ext}',
                                        duracion=solicitud.get('duracion')))
            elif tipo == 'stack':
                items = [i for i in (solicitud.get('items') or [])[:500]
                         if isinstance(i, dict) and str(i.get('url') or '').lower().startswith(('http://', 'https://'))]
                nombre = sanitize_filename(str(solicitud.get('nombre') or '').strip()[:120], restricted=False) \
                    or time.strftime('Stack %Y-%m-%d %H-%M')
                grupo = uuid.uuid4().hex[:12]
                for n, item in enumerate(items, start=1):
                    propias = item.get('prefs') if isinstance(item.get('prefs'), dict) else {}
                    p = dict(normalizar({**prefs, **propias}), _stack=True)  # _stack: siempre en su subcarpeta
                    trabajos.append(Trabajo(item['url'], p, item.get('titulo') or None, item.get('miniatura'),
                                            item.get('canal'), item.get('duracion'),
                                            titulo_formato='Auto · Stack', subcarpeta=nombre, grupo_id=grupo,
                                            indice=n, total_grupo=len(items)))
            elif tipo == 'lote':
                urls = solicitud.get('urls') or []
                grupo = uuid.uuid4().hex[:12]
                for i, url in enumerate(urls, start=1):
                    trabajos.append(Trabajo(url, prefs, titulo_formato=auto, grupo_id=grupo, indice=i,
                                            total_grupo=len(urls),
                                            quitar_anuncios=bool(solicitud.get('quitar_anuncios'))))
            if not trabajos:
                return {'ok': False, 'error': 'No hay nada seleccionado para descargar.'}
            self._gestor.agregar(trabajos)
            return _ok(agregados=len(trabajos))
        except Exception as e:  # noqa: BLE001
            return _fallo(e)

    @staticmethod
    def _validar_recorte(recorte, duracion):
        if not recorte or len(recorte) != 2:
            return None
        inicio, fin = _segundos(recorte[0]), _segundos(recorte[1])
        if inicio is None or fin is None or fin <= inicio:
            return None
        if duracion:
            fin = min(fin, float(duracion))
        return [inicio, fin] if fin > inicio else None

    def sponsor_segmentos(self, id_, categorias=None):
        """Segmentos que se quitarían con "Quitar anuncios" (solo se consulta al activarlo)."""
        datos = self._analizador.obtener(id_)
        if not datos:
            return {'ok': False, 'error': 'El análisis caducó; vuelve a analizar la URL.'}
        if datos.get('sitio_clave') not in sponsor.SITIOS:
            return {'ok': True, 'soportado': False, 'segmentos': [], 'total': 0}
        cats = sponsor.categorias_validas(categorias or self._ajustes.get('prefs').get('sponsor_cats'))
        try:
            lista = sponsor.segmentos(datos.get('video_id'), cats)
        except Exception as e:  # noqa: BLE001
            return {'ok': False, 'error': f'No se pudo consultar SponsorBlock: {e}'}
        return {'ok': True, 'soportado': True, 'segmentos': lista, 'total': sponsor.duracion_total(lista)}

    def probar_args(self, texto):
        try:
            extra, pps = interpretar(texto)
            return {'ok': True, 'opciones': sorted(extra), 'postprocesadores': [p.get('key') for p in pps]}
        except ArgumentosInvalidos as e:
            return {'ok': False, 'error': str(e)}

    def olvidar_descargados(self):
        try:
            os.unlink(ruta_archivo_descargados())
        except OSError:
            pass
        return True

    # ---------- cola ----------
    def cola(self):
        return {'trabajos': self._gestor.lista(), 'resumen': self._gestor.resumen(),
                'paralelo': self._ajustes.get('paralelo'), 'max_paralelo': self._ajustes.get('max_paralelo'),
                'limite_velocidad': self._ajustes.get('limite_velocidad')}

    def pausar_cola(self, pausar=True):
        self._gestor.pausar_cola(pausar)
        return self._gestor.resumen()

    def cerrar(self):
        self._detener_captura()
        self._gestor.cerrar()

    def cancelar(self, id_):
        return self._gestor.cancelar(id_)

    def cancelar_todo(self):
        self._gestor.cancelar_todo()
        return True

    def reintentar(self, id_):
        return self._gestor.reintentar(id_)

    def quitar(self, id_):
        return self._gestor.quitar(id_)

    def limpiar(self):
        self._gestor.limpiar()
        return True

    def abrir_archivo(self, id_):
        t = self._gestor.obtener(id_)
        if t and t.archivo and os.path.isfile(t.archivo) and not es_medio(t.archivo):
            abrir_en_explorador(t.archivo, seleccionar=True)
            return {'ok': True, 'aviso': 'Por seguridad no se abre directamente: no es un archivo multimedia. Se muestra en su carpeta.'}
        return bool(t and abrir_en_explorador(t.archivo))

    def detalle(self, id_):
        """Error completo y log de una descarga (con los tokens ya ocultos) para verlos o copiarlos."""
        t = self._gestor.obtener(id_)
        if t is None:
            return {'ok': False, 'error': 'Esa descarga ya no está en la lista.'}
        return {'ok': True, 'error': t.error_detalle or t.error, 'registro': list(t.registro),
                'completo': bool(self._ajustes.get('log_completo'))}

    def copiar(self, texto):
        """Copia al portapapeles (los tokens se ocultan también aquí, por si acaso)."""
        from .utilidades import copiar_portapapeles, ocultar_tokens
        return copiar_portapapeles(ocultar_tokens(str(texto or ''))[:200000])

    def abrir_carpeta(self, id_=None):
        t = self._gestor.obtener(id_) if id_ else None
        if t and t.archivo and os.path.exists(t.archivo):
            return abrir_en_explorador(t.archivo, seleccionar=True)
        carpeta = self._ajustes.carpeta()
        os.makedirs(carpeta, exist_ok=True)
        return abrir_en_explorador(carpeta)

    # ---------- ajustes ----------
    def ajustes(self):
        return self._ajustes.todo()

    def guardar_ajustes(self, cambios):
        todo = self._ajustes.actualizar(cambios or {})
        self._gestor.notificar()
        if any(k.startswith('captura_') for k in (cambios or {})):
            self.configurar_captura()
            todo = dict(todo, captura_error=self._error_captura())
        if 'retomar_cola' in (cambios or {}):
            self._gestor._guardar_cola()
        if 'ffmpeg_ruta' in (cambios or {}):
            threading.Thread(target=self._herr.detectar_gpu, kwargs={'forzar': True}, daemon=True).start()
        return todo

    def elegir_carpeta(self):
        ruta = self._dialogo('FOLDER', directory=self._ajustes.carpeta())
        return self.guardar_ajustes({'carpeta': ruta}) if ruta else None

    def elegir_cookies(self):
        ruta = self._dialogo('OPEN', file_types=('Cookies (*.txt)', 'Todos los archivos (*.*)'))
        return self.guardar_ajustes({'cookies_archivo': ruta, 'cookies_modo': 'archivo'}) if ruta else None

    def elegir_aria2(self):
        ruta = self._dialogo('OPEN', file_types=('Programa aria2c (*.exe)', 'Todos los archivos (*.*)'))
        if not ruta:
            return None
        todo = self.guardar_ajustes({'aria2_ruta': ruta})
        if todo.get('aria2_ruta') != ruta:
            todo['aviso'] = 'Ese archivo no es aria2c.exe; se mantiene la ruta anterior.'
        return todo

    def elegir_ffmpeg(self):
        ruta = self._dialogo('OPEN', file_types=('Programa ffmpeg (*.exe)', 'Todos los archivos (*.*)'))
        if not ruta:
            return None
        todo = self.guardar_ajustes({'ffmpeg_ruta': ruta})
        if todo.get('ffmpeg_ruta') != ruta:
            todo['aviso'] = 'Ese archivo no es ffmpeg.exe; se mantiene la ruta anterior.'
        return todo

    def importar_txt(self):
        ruta = self._dialogo('OPEN', file_types=('Listas de URLs (*.txt)', 'Todos los archivos (*.*)'))
        if not ruta:
            return None
        try:
            return _ok(urls=leer_urls_txt(ruta))
        except Exception as e:  # noqa: BLE001
            return _fallo(e)

    # ---------- stack ----------
    def _ruta_stack(self):
        return os.path.join(carpeta_datos(), 'stack.json')

    def cargar_stack(self):
        try:
            with open(self._ruta_stack(), 'r', encoding='utf-8') as f:
                datos = json.load(f)
            return datos if isinstance(datos, dict) else {}
        except (OSError, ValueError):
            return {}

    def guardar_stack(self, stack):
        """Guarda el stack para no perderlo al cerrar (solo enlace, título, miniatura, duración y prefs)."""
        from .colecciones import limpiar_item
        items = []
        for i in (stack or {}).get('items') or []:
            limpio = limpiar_item(i, permitir_rutas=False) if isinstance(i, dict) else None
            if limpio:
                propias = i.get('prefs') if isinstance(i.get('prefs'), dict) else None
                items.append({**limpio, 'prefs': {k: v for k, v in (propias or {}).items()
                                                  if k in ('tipo', 'resolucion')} or None})
        datos = {'nombre': str((stack or {}).get('nombre') or '')[:120], 'items': items[:500]}
        temporal = self._ruta_stack() + '.tmp'
        try:
            with open(temporal, 'w', encoding='utf-8') as f:
                json.dump(datos, f, ensure_ascii=False)
            os.replace(temporal, self._ruta_stack())
        except OSError:
            return False
        return True

    # ---------- colecciones ----------
    def colecciones(self):
        return self._colecciones.lista()

    def coleccion(self, id_):
        c = self._colecciones.obtener(id_)
        return _ok(coleccion=c) if c else {'ok': False, 'error': 'Esa colección ya no existe.'}

    def _col(self, funcion, *args):
        try:
            return _ok(resultado=funcion(*args), colecciones=self._colecciones.lista())
        except ColeccionInvalida as e:
            return {'ok': False, 'error': str(e)}

    def crear_coleccion(self, nombre, items=None):
        return self._col(self._colecciones.crear, nombre, items)

    def renombrar_coleccion(self, id_, nombre):
        return self._col(self._colecciones.renombrar, id_, nombre)

    def borrar_coleccion(self, id_):
        return self._col(self._colecciones.borrar, id_)

    def agregar_a_coleccion(self, id_, items):
        return self._col(self._colecciones.agregar, id_, items)

    def quitar_de_coleccion(self, id_, item):
        return self._col(self._colecciones.quitar, id_, item)

    def reordenar_coleccion(self, id_, desde, hasta):
        return self._col(self._colecciones.reordenar, id_, int(desde), int(hasta))

    def alternar_favorito(self, item):
        return self._col(self._colecciones.alternar_favorito, item)

    def exportar_coleccion(self, id_, tipo='jabs', progreso=False):
        c = self._colecciones.obtener(id_)
        if not c:
            return {'ok': False, 'error': 'Esa colección ya no existe.'}
        nombre = sanitize_filename(c['nombre'].replace('★', '').strip(), restricted=False) or 'coleccion'
        extension = 'txt' if tipo == 'txt' else 'jabs'
        filtro = ('Lista de enlaces (*.txt)',) if extension == 'txt' else ('Colección JabsDLP (*.jabs)',)
        ruta = self._dialogo('SAVE', save_filename=f'{nombre}.{extension}', file_types=filtro)
        if not ruta:
            return None
        if not ruta.lower().endswith('.' + extension):
            ruta += '.' + extension
        try:
            return _ok(**self._colecciones.exportar(id_, ruta, extension, bool(progreso)), ruta=ruta)
        except (OSError, ColeccionInvalida) as e:
            return {'ok': False, 'error': f'No se pudo exportar: {e}'}

    def importar_coleccion(self):
        ruta = self._dialogo('OPEN', file_types=('Colecciones (*.jabs;*.txt)', 'Todos los archivos (*.*)'))
        if not ruta:
            return None
        try:
            id_, cantidad = self._colecciones.importar(ruta)
            return _ok(id=id_, cantidad=cantidad, colecciones=self._colecciones.lista())
        except (OSError, ColeccionInvalida) as e:
            return {'ok': False, 'error': str(e) if isinstance(e, ColeccionInvalida) else f'No se pudo leer: {e}'}

    def descargar_coleccion(self, id_, prefs=None):
        c = self._colecciones.obtener(id_)
        if not c:
            return {'ok': False, 'error': 'Esa colección ya no existe.'}
        enlaces = [i for i in c['items'] if 'url' in i]
        if not enlaces:
            return {'ok': False, 'error': 'La colección no tiene enlaces para descargar (solo archivos ya descargados).'}
        return self.descargar({'tipo': 'stack', 'items': enlaces, 'nombre': c['nombre'].replace('★', '').strip(),
                               'prefs': prefs})

    # ---------- biblioteca ----------
    def _raices(self):
        raices = [self._ajustes.carpeta()] + list(self._ajustes.get('carpetas_biblioteca') or [])
        vistas, limpias = set(), []
        for r in raices:
            clave = os.path.normcase(os.path.abspath(r))
            if clave not in vistas and os.path.isdir(r):
                vistas.add(clave)
                limpias.append(os.path.abspath(r))
        return limpias

    def biblioteca_carpetas(self):
        principal = os.path.normcase(os.path.abspath(self._ajustes.carpeta()))
        return [{'ruta': r, 'nombre': os.path.basename(r.rstrip('\\/')) or r,
                 'principal': os.path.normcase(r) == principal} for r in self._raices()]

    def biblioteca_listar(self, raiz, sub=''):
        raices = self._raices()
        if not any(os.path.normcase(os.path.abspath(raiz or '')) == os.path.normcase(r) for r in raices):
            return {'ok': False, 'error': 'Esa carpeta no está en la Biblioteca.'}
        try:
            datos = biblioteca.listar(raiz, sub, raices)
        except biblioteca.RutaNoPermitida as e:
            return {'ok': False, 'error': str(e)}
        favoritos = self._colecciones.favoritos_rutas()
        for a in datos['archivos']:
            a['favorito'] = os.path.normcase(a['ruta']) in favoritos
        return _ok(**datos)

    def biblioteca_miniatura(self, ruta):
        if not ruta or not biblioteca.dentro_de(ruta, self._raices()):
            return None
        return biblioteca.miniatura(ruta, self._herr.ffmpeg())

    def biblioteca_agregar_carpeta(self):
        ruta = self._dialogo('FOLDER', directory=self._ajustes.carpeta())
        if not ruta:
            return None
        actuales = list(self._ajustes.get('carpetas_biblioteca') or [])
        self._ajustes.actualizar({'carpetas_biblioteca': actuales + [ruta]})
        return _ok(carpetas=self.biblioteca_carpetas(), ruta=os.path.abspath(ruta))

    def biblioteca_quitar_carpeta(self, ruta):
        actuales = [c for c in (self._ajustes.get('carpetas_biblioteca') or [])
                    if os.path.normcase(os.path.abspath(c)) != os.path.normcase(os.path.abspath(ruta or ''))]
        self._ajustes.actualizar({'carpetas_biblioteca': actuales})
        return _ok(carpetas=self.biblioteca_carpetas())

    def biblioteca_abrir(self, ruta, carpeta=False):
        if not ruta or not biblioteca.dentro_de(ruta, self._raices()) or not os.path.exists(ruta):
            return {'ok': False, 'error': 'No se encontró el archivo (¿lo moviste o borraste?).'}
        if carpeta or not es_medio(ruta):
            return _ok(hecho=abrir_en_explorador(ruta, seleccionar=True))
        return _ok(hecho=abrir_en_explorador(ruta))

    def biblioteca_papelera(self, rutas):
        movidos, fallidos = 0, 0
        for ruta in (rutas or [])[:500]:
            if isinstance(ruta, str) and biblioteca.dentro_de(ruta, self._raices()) and biblioteca.papelera(ruta):
                movidos += 1
            else:
                fallidos += 1
        return _ok(movidos=movidos, fallidos=fallidos)

    # ---------- ventana ----------
    def _hwnd(self):
        try:
            return self._ventana.native.Handle.ToInt32() if self._ventana and self._ventana.native else None
        except Exception:  # noqa: BLE001
            return ventana.hwnd_por_titulo(APP_NAME)

    def aplicar_tema_ventana(self, claro):
        return ventana.tema_barra(self._hwnd(), bool(claro))

    def alternar_pantalla_completa(self):
        if self._ventana is not None:
            self._ventana.toggle_fullscreen()
        return True

    # ---------- captura rápida (atajo y portapapeles) ----------
    def _error_captura(self):
        return self._atajo.error if self._atajo and self._atajo.error else None

    def _detener_captura(self):
        if self._atajo:
            self._atajo.detener()
        if self._vigia:
            self._vigia.detener()
        self._atajo = self._vigia = None

    def configurar_captura(self):
        """Arranca o para el atajo y el vigía según los ajustes. Devuelve el error del atajo, si lo hay."""
        self._detener_captura()
        if os.name != 'nt':
            return None
        if self._ajustes.get('captura_atajo'):
            try:
                self._atajo = captura.Atajo(self._ajustes.get('captura_tecla'), self._recibir_captura)
                self._atajo.iniciar()
            except ValueError as e:
                self._atajo = None
                return str(e)
        if self._ajustes.get('captura_portapapeles'):
            self._vigia = captura.VigiaPortapapeles(self._recibir_captura, captura.sitio_reconocido)
            self._vigia.iniciar()
        return self._error_captura()

    def estado_captura(self):
        return {'error': self._error_captura(), 'atajo': bool(self._atajo and not self._atajo.error),
                'portapapeles': bool(self._vigia)}

    def _enviar_a_la_interfaz(self, urls, accion='auto'):
        if self._ventana is None:
            return
        try:
            self._ventana.evaluate_js(f'recibirCaptura({json.dumps(urls)}, {json.dumps(accion)})')
        except Exception:  # noqa: BLE001 - la ventana pudo cerrarse
            return
        visible = True
        try:
            hwnd = self._hwnd()
            import ctypes
            visible = bool(hwnd and ctypes.windll.user32.IsWindowVisible(hwnd) and not ctypes.windll.user32.IsIconic(hwnd))
        except Exception:  # noqa: BLE001
            pass
        if not visible and self._ajustes.get('notificaciones'):
            destino = 'stack' if self._ajustes.get('modo_stack') else 'JabsDLP'
            notificar.mostrar(f'Enviado a {destino}', urls[0][:120], None, None, self._icono_avisos)

    def _recibir_captura(self, urls, desde_atajo):
        """Del atajo (siempre se envía) o del vigía del portapapeles (sugerir con la burbuja o enviar)."""
        if desde_atajo or self._ajustes.get('captura_modo') == 'auto':
            self._enviar_a_la_interfaz(urls)
        else:
            self._sugerir(urls[0])

    def _sugerir(self, url):
        if self._burbuja is None or captura.pantalla_completa_activa():
            return
        from urllib.parse import urlsplit
        self._sugerida = url
        datos = {'url': url, 'dominio': (urlsplit(url).hostname or '').removeprefix('www.'),
                 'stack': bool(self._ajustes.get('modo_stack')), 'idioma': self.idioma(),
                 'claro': self._ajustes.get('tema') == 'claro'}
        try:
            self._burbuja.evaluate_js(f'mostrar({json.dumps(datos)})')
        except Exception:  # noqa: BLE001
            return
        hwnd = ventana.hwnd_por_titulo('JabsDLP · enlace')
        if hwnd:
            izq, arriba, der, abajo = captura.area_trabajo()
            esc = ventana.escala(hwnd)
            ancho, alto = int(372 * esc), int(104 * esc)
            x, y = der - ancho - int(16 * esc), abajo - alto - int(16 * esc)
            ventana.mostrar_sin_foco(hwnd, x, y, ancho, alto)
            # La primera vez que se muestra, WinForms la recoloca: se vuelve a poner en su sitio
            for espera in (0.15, 0.5):
                threading.Timer(espera, ventana.mostrar_sin_foco, args=(hwnd, x, y, ancho, alto)).start()
        else:
            self._burbuja.show()
        if self._temporizador_burbuja:
            self._temporizador_burbuja.cancel()
        self._temporizador_burbuja = threading.Timer(7.0, self._ocultar_burbuja)
        self._temporizador_burbuja.daemon = True
        self._temporizador_burbuja.start()

    def _ocultar_burbuja(self):
        self._sugerida = None
        hwnd = ventana.hwnd_por_titulo('JabsDLP · enlace')
        if hwnd:
            ventana.ocultar(hwnd)
        elif self._burbuja is not None:
            try:
                self._burbuja.hide()
            except Exception:  # noqa: BLE001
                pass

    def burbuja_accion(self, accion):
        """Botones de la burbuja: 'stack' | 'descargar' | 'cerrar'."""
        url = self._sugerida
        self._ocultar_burbuja()
        if url and accion in ('stack', 'descargar'):
            self._enviar_a_la_interfaz([url], accion)
        return True

    def burbuja_mantener(self):
        """El ratón está encima de la burbuja: no se cierra mientras tanto."""
        if self._temporizador_burbuja:
            self._temporizador_burbuja.cancel()
        return True

    def burbuja_soltar(self):
        if self._sugerida:
            self._temporizador_burbuja = threading.Timer(3.0, self._ocultar_burbuja)
            self._temporizador_burbuja.daemon = True
            self._temporizador_burbuja.start()
        return True

    def portapapeles(self):
        try:
            return leer_portapapeles()
        except OSError:
            return ''
