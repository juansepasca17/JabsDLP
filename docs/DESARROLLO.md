# Desarrollo

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
| `jabsdlp/actualizador.py` | Actualización de yt-dlp (estable o nightly) sin recompilar |
| `jabsdlp/ver.py`, `proxy.py`, `ver_torrent.py` | Pestaña Ver: resolver la fuente, proxy local y torrents |
| `jabsdlp/biblioteca.py`, `colecciones.py` | Biblioteca de archivos y colecciones |
| `jabsdlp/captura.py` | Atajo global y vigía del portapapeles |
| `jabsdlp/registro_app.py` | Log propio de la app |
| `ui/` | Interfaz (HTML, CSS y JS; solo `ui/vendor/hls.min.js` es de terceros) |
| `android/` | App de Android (Kotlin + Chaquopy), reutiliza `ui/` y `jabsdlp/` |

## Android

La versión de Android está en `android/` y usa las mismas carpetas `ui/` y `jabsdlp/`. Cómo está hecha y cómo se pasa una versión nueva: [android/PORTAR.md](../android/PORTAR.md).
