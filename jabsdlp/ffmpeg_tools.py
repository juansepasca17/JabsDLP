"""ffmpeg: localizarlo, descargarlo, detectar la GPU y recodificar a H.265/H.264."""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.request
import zipfile

from .ajustes import carpeta_local
from .utilidades import SIN_VENTANA, Cancelado

URL_BASE_FFMPEG = 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/'
ZIP_FFMPEG = 'ffmpeg-master-latest-win64-gpl.zip'

ENCODERS = {
    'h265': {'nvenc': 'hevc_nvenc', 'amf': 'hevc_amf', 'qsv': 'hevc_qsv', 'cpu': 'libx265'},
    'h264': {'nvenc': 'h264_nvenc', 'amf': 'h264_amf', 'qsv': 'h264_qsv', 'cpu': 'libx264'},
}
NOMBRES = {'nvenc': 'NVIDIA NVENC', 'amf': 'AMD AMF', 'qsv': 'Intel QSV', 'cpu': 'CPU'}
GPUS = ('nvenc', 'amf', 'qsv')


def _carpeta_app():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Limitador:
    """Semáforo cuyo límite se lee de los ajustes en cada espera (se puede cambiar en caliente)."""

    def __init__(self, limite):
        self._limite = limite
        self._cv = threading.Condition()
        self._activos = 0

    def entrar(self, trabajo=None):
        with self._cv:
            while self._activos >= max(1, int(self._limite() or 1)):
                if trabajo is not None and trabajo.cancelado:
                    raise Cancelado()
                self._cv.wait(0.5)
            self._activos += 1

    def salir(self):
        with self._cv:
            self._activos -= 1
            self._cv.notify_all()


class Herramientas:
    def __init__(self, ajustes):
        self._ajustes = ajustes
        self._gpu = None
        self._lock = threading.Lock()
        self.conversiones = Limitador(lambda: ajustes.get('max_conversiones'))
        self.descarga = {'estado': 'inactivo', 'progreso': 0.0, 'error': None}

    # ---------- localizar ----------
    def ffmpeg(self):
        candidatos = []
        configurada = (self._ajustes.get('ffmpeg_ruta') or '').strip().strip('"')
        if configurada:
            candidatos.append(configurada if configurada.lower().endswith('.exe') else os.path.join(configurada, 'ffmpeg.exe'))
        base = _carpeta_app()
        candidatos += [os.path.join(base, 'ffmpeg.exe'), os.path.join(base, 'ffmpeg', 'ffmpeg.exe')]
        en_path = shutil.which('ffmpeg')
        if en_path:
            candidatos.append(en_path)
        candidatos.append(os.path.join(carpeta_local(), 'ffmpeg', 'ffmpeg.exe'))
        for ruta in candidatos:
            if ruta and os.path.isfile(ruta):
                return ruta
        return None

    def ffprobe(self):
        ff = self.ffmpeg()
        if not ff:
            return None
        ruta = os.path.join(os.path.dirname(ff), 'ffprobe.exe' if os.name == 'nt' else 'ffprobe')
        return ruta if os.path.isfile(ruta) else shutil.which('ffprobe')

    # ---------- GPU ----------
    def detectar_gpu(self, forzar=False):
        with self._lock:
            if self._gpu is not None and not forzar:
                return dict(self._gpu)
            resultado = {k: False for k in GPUS}
            ff = self.ffmpeg()
            if ff:
                for tipo in GPUS:
                    comando = [ff, '-hide_banner', '-loglevel', 'error', '-f', 'lavfi',
                               '-i', 'color=c=black:s=256x256:r=30', '-frames:v', '3',
                               '-c:v', ENCODERS['h265'][tipo], '-f', 'null', '-']
                    try:
                        proc = subprocess.run(comando, capture_output=True, timeout=30, creationflags=SIN_VENTANA)
                        resultado[tipo] = proc.returncode == 0
                    except (OSError, subprocess.TimeoutExpired):
                        resultado[tipo] = False
            self._gpu = resultado
            return dict(resultado)

    def tipo_encoder(self):
        modo = self._ajustes.get('gpu')
        if modo == 'cpu':
            return 'cpu'
        gpu = self.detectar_gpu()
        if modo in GPUS:
            return modo if gpu.get(modo) else 'cpu'
        for tipo in GPUS:
            if gpu.get(tipo):
                return tipo
        return 'cpu'

    def descripcion_encoder(self, objetivo='h265'):
        tipo = self.tipo_encoder()
        return {'tipo': tipo, 'nombre': NOMBRES[tipo], 'encoder': ENCODERS[objetivo][tipo], 'gpu': tipo != 'cpu'}

    def _args_video(self, tipo, objetivo):
        calidad = int(self._ajustes.get('calidad') or 26)
        encoder = ENCODERS[objetivo][tipo]
        if tipo == 'amf':
            args = ['-c:v', encoder, '-quality', 'quality', '-rc', 'cqp', '-qp_i', str(calidad), '-qp_p', str(calidad)]
        elif tipo == 'nvenc':
            args = ['-c:v', encoder, '-preset', 'p5', '-rc', 'vbr', '-cq', str(calidad), '-b:v', '0']
        elif tipo == 'qsv':
            args = ['-c:v', encoder, '-global_quality', str(calidad)]
        else:
            args = ['-c:v', encoder, '-crf', str(calidad + 2), '-preset', 'medium']
        if objetivo == 'h265':
            args += ['-tag:v', 'hvc1']
        else:
            args += ['-pix_fmt', 'yuv420p']
        return args

    # ---------- recodificar ----------
    def recodificar(self, entrada, salida, objetivo, duracion, trabajo, copiar_audio=True):
        tipo = self.tipo_encoder()
        intentos = [tipo] if tipo == 'cpu' else [tipo, 'cpu']
        error = ''
        for intento in intentos:
            trabajo.encoder = f'{NOMBRES[intento]} ({ENCODERS[objetivo][intento]})'
            ok, error = self._ejecutar(entrada, salida, objetivo, intento, duracion, trabajo, copiar_audio)
            if ok:
                return intento
            if trabajo.cancelado:
                raise Cancelado()
            if intento != 'cpu':
                trabajo.aviso = f'La GPU ({NOMBRES[intento]}) falló al convertir; se usó la CPU.'
        raise RuntimeError(f'ffmpeg no pudo convertir el video: {error[-300:]}')

    def _ejecutar(self, entrada, salida, objetivo, tipo, duracion, trabajo, copiar_audio):
        ff = self.ffmpeg()
        if not ff:
            raise RuntimeError('Falta ffmpeg. Descárgalo desde Ajustes → Herramientas.')
        comando = [ff, '-hide_banner', '-nostdin', '-y', '-loglevel', 'error', '-progress', 'pipe:1', '-nostats']
        if tipo != 'cpu' and self._ajustes.get('decodificar_gpu'):
            comando += ['-hwaccel', 'auto']
        comando += ['-i', entrada, '-map', '0:v:0', '-map', '0:a?', '-map_metadata', '0', '-map_chapters', '0']
        comando += self._args_video(tipo, objetivo)
        comando += ['-c:a', 'copy'] if copiar_audio else ['-c:a', 'aac', '-b:a', '192k']
        if salida.lower().endswith(('.mp4', '.m4v', '.mov')):
            comando += ['-movflags', '+faststart']
        comando.append(salida)

        with tempfile.TemporaryFile() as errores:
            proc = subprocess.Popen(comando, stdout=subprocess.PIPE, stderr=errores, creationflags=SIN_VENTANA,
                                    text=True, encoding='utf-8', errors='replace')
            trabajo.proceso = proc
            try:
                for linea in proc.stdout:
                    if trabajo.cancelado:
                        proc.kill()
                        break
                    clave, _, valor = linea.strip().partition('=')
                    if clave == 'out_time_us' and valor.isdigit() and duracion:
                        trabajo.progreso_conversion = min(1.0, int(valor) / 1e6 / duracion)
                    elif clave == 'speed':
                        trabajo.velocidad_conversion = valor
                proc.wait()
            finally:
                trabajo.proceso = None
            errores.seek(0)
            texto_error = errores.read().decode('utf-8', 'replace')
        if proc.returncode != 0 and os.path.exists(salida):
            try:
                os.unlink(salida)
            except OSError:
                pass
        return proc.returncode == 0 and not trabajo.cancelado, texto_error

    # ---------- descargar ffmpeg ----------
    def descargar_ffmpeg(self):
        if self.descarga['estado'] == 'descargando':
            return self.descarga
        self.descarga = {'estado': 'descargando', 'progreso': 0.0, 'error': None}
        threading.Thread(target=self._descargar_ffmpeg, daemon=True).start()
        return self.descarga

    def _descargar_ffmpeg(self):
        destino = os.path.join(carpeta_local(), 'ffmpeg')
        zip_tmp = os.path.join(carpeta_local(), 'ffmpeg-descarga.zip')
        try:
            esperado = self._checksum_ffmpeg()
            sha = hashlib.sha256()
            peticion = urllib.request.Request(URL_BASE_FFMPEG + ZIP_FFMPEG, headers={'User-Agent': 'JabsDLP'})
            with urllib.request.urlopen(peticion, timeout=60) as resp, open(zip_tmp, 'wb') as f:
                total = int(resp.headers.get('Content-Length') or 0)
                hecho = 0
                while True:
                    bloque = resp.read(1 << 20)
                    if not bloque:
                        break
                    f.write(bloque)
                    sha.update(bloque)
                    hecho += len(bloque)
                    if total:
                        self.descarga['progreso'] = hecho / total * 0.95
            if sha.hexdigest() != esperado:
                raise RuntimeError('La suma SHA-256 del ffmpeg descargado no coincide; se descartó por seguridad.')
            self.descarga['estado'] = 'extrayendo'
            os.makedirs(destino, exist_ok=True)
            with zipfile.ZipFile(zip_tmp) as z:
                for miembro in z.namelist():
                    nombre = os.path.basename(miembro)
                    if miembro.endswith(('/bin/ffmpeg.exe', '/bin/ffprobe.exe')):
                        with z.open(miembro) as origen, open(os.path.join(destino, nombre), 'wb') as salida:
                            shutil.copyfileobj(origen, salida)
            if not os.path.isfile(os.path.join(destino, 'ffmpeg.exe')):
                raise RuntimeError('El archivo descargado no contiene ffmpeg.exe')
            with self._lock:
                self._gpu = None
            self.descarga = {'estado': 'listo', 'progreso': 1.0, 'error': None}
        except Exception as e:  # noqa: BLE001 - se muestra al usuario
            self.descarga = {'estado': 'error', 'progreso': 0.0, 'error': str(e)}
        finally:
            if os.path.exists(zip_tmp):
                try:
                    os.unlink(zip_tmp)
                except OSError:
                    pass

    @staticmethod
    def _checksum_ffmpeg():
        """SHA-256 publicado por el autor del build (checksums.sha256 de la misma release)."""
        peticion = urllib.request.Request(URL_BASE_FFMPEG + 'checksums.sha256', headers={'User-Agent': 'JabsDLP'})
        with urllib.request.urlopen(peticion, timeout=30) as resp:
            for linea in resp.read().decode('utf-8', 'replace').splitlines():
                partes = linea.split()
                if len(partes) == 2 and partes[1].lstrip('*') == ZIP_FFMPEG:
                    return partes[0].lower()
        raise RuntimeError('No se pudo verificar la descarga de ffmpeg (falta su suma SHA-256).')

    def estado(self):
        ff = self.ffmpeg()
        return {
            'ffmpeg': ff,
            'ffprobe': self.ffprobe(),
            'gpu': self._gpu,
            'descarga': dict(self.descarga),
        }
