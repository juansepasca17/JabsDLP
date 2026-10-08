"""Puente entre la interfaz (JavaScript) y el motor. pywebview expone los métodos públicos."""
import os
import threading

import yt_dlp

from . import APP_NAME, VERSION
from .ajustes import Ajustes
from .cookies import limpiar_temporales_huerfanos
from .analizador import Analizador
from .ffmpeg_tools import Herramientas
from .formatos import NOMBRE_CRITERIO, calcular, normalizar
from .gestor import Gestor
from .trabajo import Trabajo
from .utilidades import abrir_en_explorador, error_amigable, extraer_urls, leer_portapapeles, leer_urls_txt, runtimes_js


def _ok(**datos):
    return {'ok': True, **datos}


def _fallo(e):
    return {'ok': False, 'error': error_amigable(e)}


class Api:
    def __init__(self):
        limpiar_temporales_huerfanos()
        self._ajustes = Ajustes()
        self._herr = Herramientas(self._ajustes)
        self._analizador = Analizador(self._ajustes)
        self._gestor = Gestor(self._ajustes, self._herr)
        self._ventana = None
        threading.Thread(target=self._herr.detectar_gpu, daemon=True).start()

    def _dialogo(self, tipo, **kwargs):
        import webview
        if self._ventana is None:
            return None
        resultado = self._ventana.create_file_dialog(getattr(webview.FileDialog, tipo), **kwargs)
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
        return estado

    def detectar_gpu(self):
        self._herr.detectar_gpu(forzar=True)
        return self.herramientas()

    def descargar_ffmpeg(self):
        return self._herr.descargar_ffmpeg()

    # ---------- analizar ----------
    def analizar(self, url, modo='auto', prefs=None):
        url = (url or '').strip()
        urls = extraer_urls(url)
        if len(urls) > 1:
            return _ok(datos={'tipo': 'lote', 'id': None, 'urls': urls, 'cantidad': len(urls)})
        if not urls:
            return {'ok': False, 'error': 'Pega una URL válida (debe empezar por http).'}
        try:
            datos = self._analizador.analizar(urls[0], modo)
            if datos['tipo'] == 'video':
                datos.update(self.opciones(datos['id'], prefs or self._ajustes.get('prefs')))
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
                trabajos.append(Trabajo(
                    datos['url'], prefs, datos['titulo'], datos['miniatura'], datos['canal'], datos['duracion'],
                    formato=elegida['spec'] if elegida else None,
                    contenedor=elegida.get('contenedor') if elegida and prefs.get('tipo') != 'audio' else None,
                    titulo_formato=elegida['titulo'] if elegida else 'Auto',
                    tamano=elegida.get('tamano') if elegida else None,
                ))
            elif tipo == 'playlist':
                datos = self._analizador.obtener(solicitud.get('id'))
                if not datos:
                    return {'ok': False, 'error': 'El análisis caducó; vuelve a analizar la URL.'}
                elegidos = set(solicitud.get('indices') or [e['indice'] for e in datos['entradas']])
                for e in datos['entradas']:
                    if e['indice'] in elegidos:
                        trabajos.append(Trabajo(e['url'], prefs, e['titulo'], e['miniatura'], e['canal'] or datos['canal'],
                                                e['duracion'], titulo_formato=auto, subcarpeta=datos['titulo']))
            elif tipo == 'lote':
                for url in solicitud.get('urls') or []:
                    trabajos.append(Trabajo(url, prefs, titulo_formato=auto))
            if not trabajos:
                return {'ok': False, 'error': 'No hay nada seleccionado para descargar.'}
            self._gestor.agregar(trabajos)
            return _ok(agregados=len(trabajos))
        except Exception as e:  # noqa: BLE001
            return _fallo(e)

    # ---------- cola ----------
    def cola(self):
        return {'trabajos': self._gestor.lista(), 'resumen': self._gestor.resumen(),
                'paralelo': self._ajustes.get('paralelo'), 'max_paralelo': self._ajustes.get('max_paralelo')}

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
        return bool(t and abrir_en_explorador(t.archivo))

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
        if 'ffmpeg_ruta' in (cambios or {}):
            threading.Thread(target=self._herr.detectar_gpu, kwargs={'forzar': True}, daemon=True).start()
        return todo

    def elegir_carpeta(self):
        ruta = self._dialogo('FOLDER', directory=self._ajustes.carpeta())
        return self.guardar_ajustes({'carpeta': ruta}) if ruta else None

    def elegir_cookies(self):
        ruta = self._dialogo('OPEN', file_types=('Cookies (*.txt)', 'Todos los archivos (*.*)'))
        return self.guardar_ajustes({'cookies_archivo': ruta, 'cookies_modo': 'archivo'}) if ruta else None

    def elegir_ffmpeg(self):
        ruta = self._dialogo('OPEN', file_types=('ffmpeg (ffmpeg.exe)', 'Todos los archivos (*.*)'))
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

    def portapapeles(self):
        try:
            return leer_portapapeles()
        except OSError:
            return ''
