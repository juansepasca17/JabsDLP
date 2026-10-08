# JabsDLP

Descargador de videos para Windows: rápido, en paralelo y sin opciones de más. Pegas un enlace y te propone
**una opción recomendada**. Si quieres, eliges a mano de la lista. Por dentro usa [yt-dlp](https://github.com/yt-dlp/yt-dlp)
y [ffmpeg](https://ffmpeg.org).

## Qué hace

- **Videos, playlists y canales** de YouTube y de cientos de sitios más. También acepta varias URLs a la vez o un `.txt` con una URL por línea.
- **Miniatura y metadatos** antes de descargar: duración, vistas, likes, fecha, resolución, bitrate y fps.
- **Opción recomendada (Auto)** con tres criterios:
  - *Menor tamaño sin perder calidad*: máxima resolución con el códec más eficiente (AV1 › VP9 › H.264).
  - *Menor tamaño (sacrifica calidad)*: hasta 720p, menos fps y audio medio.
  - *Mejor calidad*: el mayor bitrate disponible.
- **Personalizado**: la lista completa de formatos para elegir a mano.
- **Preferencias**: códec (Auto, H.264, H.265, AV1, VP9), resolución y contenedor (MP4, MKV, WEBM).
  - Audio: con audio, sin audio, o personalizado (eliges la pista o la calidad).
  - Solo audio: MP3, M4A, OPUS o FLAC, con o sin metadatos y portada.
- **Conversión a H.265/H.264 con la GPU** (AMD AMF, NVIDIA NVENC o Intel Quick Sync), con decodificación por GPU. Se puede dejar en Auto o desactivar para usar la CPU.
- **Descargas en paralelo sin límite**: se pueden desactivar o limitar, y hay un límite aparte de conversiones simultáneas para no saturar la GPU.
- **Cookies** desde un archivo `cookies.txt` o desde el navegador, para videos privados, con restricción de edad o cuando YouTube pide iniciar sesión.

## Requisitos

- Windows 10 u 11 con **Microsoft Edge WebView2**, que ya viene en Windows 11.
- **ffmpeg**: la app usa el que tengas instalado. Si no lo encuentra, lo descarga desde *Ajustes → Herramientas*, del build oficial de [BtbN](https://github.com/BtbN/FFmpeg-Builds), y verifica su SHA-256.
- Para YouTube, **Node.js** o **Deno** instalado: yt-dlp lo necesita para ver todos los formatos.

## Privacidad

- No hay telemetría ni cuentas. La app solo se conecta a los sitios de los que descargas y, si lo pides, a GitHub para bajar ffmpeg.
- Los ajustes y el historial se guardan solo en tu equipo, en `%APPDATA%\JabsDLP`.
- De las cookies solo se guarda la **ruta** del archivo, nunca su contenido. Para cada descarga se usa una copia temporal normalizada que se borra al terminar. Si la app se cierra de golpe, esa copia se borra al volver a abrirla.

## Compilar el .exe

```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

Crea el entorno, instala las dependencias, genera el logo, ejecuta las pruebas, compila `dist\JabsDLP.exe` con
PyInstaller y pasa la revisión de privacidad (`scripts\revisar_privacidad.py`).

Para ejecutarla desde el código: `python main.py` (con `--debug` se abren las herramientas de desarrollo).

## Estructura

| Ruta | Contenido |
| --- | --- |
| `main.py` | Ventana (pywebview) y arranque |
| `jabsdlp/formatos.py` | Opción recomendada, criterios y selectores de formato |
| `jabsdlp/gestor.py` | Cola: paralelo ilimitado o limitado, cancelar y reintentar |
| `jabsdlp/trabajo.py` | Cada descarga con yt-dlp, su progreso y la conversión por GPU |
| `jabsdlp/ffmpeg_tools.py` | Localizar o descargar ffmpeg, detectar la GPU y recodificar |
| `jabsdlp/cookies.py` | Normalización de cookies Netscape |
| `ui/` | Interfaz (HTML, CSS y JS sin dependencias externas) |

## Aviso

Usa JabsDLP solo con contenido que tengas derecho a descargar y respeta los términos de cada sitio.

Licencia MIT.
