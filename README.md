<img width="144" height="144" alt="image" src="https://github.com/user-attachments/assets/894f90ec-2caa-4a99-9b49-22ef737c55bf" />

# JabsDLP

Descargador y reproductor de videos para **Windows** y **Android**. Pegas un enlace y te propone la mejor opción;
también puedes verlo sin descargarlo. Por dentro usa [yt-dlp](https://github.com/yt-dlp/yt-dlp) y [ffmpeg](https://ffmpeg.org).

## Descargar

**[Última versión](https://github.com/juansepasca17/JabsDLP/releases/latest)**:
- **PC:** `JabsDLP.exe`, un solo archivo, sin instalador.
- **Android:** `JabsDLP-<versión>-android.apk`, para celulares de 64 bits con Android 7 o superior.

## Qué hace

- **Descarga** videos, playlists y canales de YouTube y de cientos de sitios, en paralelo, con una opción recomendada
  o eligiendo el formato a mano. También audio (MP3, M4A, OPUS, FLAC) con portada, torrents y enlaces `.m3u8`/`.mpd`.
- **Ver sin descargar**: reproductor propio con subtítulos, idioma del audio, calidad y torrents mientras se descargan.
- **Organiza**: Biblioteca de lo descargado, colecciones (también para guardar enlaces y torrents), stack para juntar
  enlaces y perfiles de descarga.
- **Rápido de usar**: atajos para mandar un enlace desde cualquier programa (PC) o *Compartir → JabsDLP* (Android).
- **Conversión con la GPU** (AMD, NVIDIA o Intel) en PC, y yt-dlp se actualiza desde la app.

Lo nuevo de cada versión: [CAMBIOS.md](CAMBIOS.md).

## Requisitos

- **PC:** Windows 10 u 11. ffmpeg lo descarga la propia app si no lo tienes. Para YouTube, Node.js o Deno instalado.
- **Android:** 7.0 o superior, 64 bits. ffmpeg y lo demás ya vienen dentro.

## Privacidad

Sin cuentas ni telemetría: todo se guarda en tu equipo. Detalles de seguridad y privacidad en
[docs/SEGURIDAD.md](docs/SEGURIDAD.md). Para compilarla: [docs/DESARROLLO.md](docs/DESARROLLO.md).

## Aviso

Usa JabsDLP solo con contenido que tengas derecho a descargar y respeta los términos de cada sitio. Licencia MIT.
