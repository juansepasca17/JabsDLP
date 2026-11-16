# Seguridad y privacidad

## Seguridad

- **aria2 nunca recibe streams HLS/DASH**: solo descargas directas (http/ftp). Así se evita [CVE-2026-50574](https://github.com/advisories/GHSA-vx4q-3cr2-7cg2), una inyección de opciones en aria2c desde manifiestos DASH. Además, el yt-dlp incluido (2026.8.19 o posterior) ya trae la corrección, y aria2 se desactiva si alguna vez se cargara un yt-dlp anterior a 2026.6.9.
- aria2 se ejecuta sin leer configuraciones externas (`--no-conf`) y sin seguir enlaces `.torrent` ni metalink que devuelva un servidor. Se copia a una carpeta propia para no meter otros ejecutables en el PATH.
- **Torrents**: se descargan con `--seed-time=0`, así que no se comparten al terminar. Mientras se descargan se sube un poco, limitado en Ajustes. Antes de empezar se avisa de los riesgos.
- **Avisos de fuente de riesgo**: torrents, enlaces `http://` sin cifrar, sitios no reconocidos (extractor genérico) y ejecutables o comprimidos. Puedes seguir o cancelar, y marcar "No volver a mostrar".
- JabsDLP **nunca ejecuta** un archivo descargado que no sea multimedia: lo muestra en su carpeta.
- Las notificaciones escapan el título del video, de modo que un título malicioso no puede ejecutar código en PowerShell. El comando personalizado solo acepta opciones de una lista de permitidas y bloquea, diciendo por qué, `--exec`, `--use-postprocessor`, `--plugin-dirs`, `--downloader` y otras que ejecutan programas o cargan código.
- Los tokens de los enlaces directos (.m3u8/.mpd) se ocultan en el log, la interfaz y el historial.
- El yt-dlp descargado solo se carga si su nombre, origen y SHA-256 son los esperados.
- ffmpeg, aria2 y el resto de procesos hijos se cierran con la app aunque esta termine de golpe (*Job Object* de Windows).

## Privacidad

- No hay telemetría ni cuentas. La app solo se conecta a los sitios de los que descargas, a PyPI para buscar actualizaciones de yt-dlp y, si lo pides, a GitHub para bajar ffmpeg.
- **curl_cffi** va dentro del `.exe` y solo se usa para las peticiones que ya hace yt-dlp (suplantando a Chrome si activas ese ajuste); no abre conexiones propias ni añade seguimiento.
- Los ajustes y el historial se guardan solo en tu equipo, en `%APPDATA%\JabsDLP`. Las versiones de yt-dlp descargadas van a `%LOCALAPPDATA%\JabsDLP\yt-dlp`.
- De las cookies solo se guarda la **ruta** del archivo, nunca su contenido. Para cada descarga se usa una copia temporal normalizada que se borra al terminar. Si la app se cierra de golpe, esa copia se borra al volver a abrirla.
