'use strict';
/* Traducción de la interfaz (español → inglés).

   La interfaz está escrita en español. En inglés, un MutationObserver traduce cada texto que aparece en pantalla
   (y los atributos title/placeholder) buscándolo en este diccionario o en los patrones de abajo; los textos con
   " · " se traducen por partes. Lo marcado con .no-traducir (títulos de videos, canales, rutas) nunca se toca.
   Al volver a español se restauran los textos originales. */
(function () {
  const EN = {
    // Navegación y búsqueda
    'Descargar': 'Download', 'Cola': 'Queue', 'Ajustes': 'Settings', 'Cola de descargas': 'Download queue',
    'Carpeta': 'Folder', 'Buscar': 'Search', 'Analizar': 'Analyze', 'Analizando…': 'Analyzing…', 'Metadatos': 'Metadata',
    'Opciones de descarga': 'Download options', 'Lote de enlaces': 'Batch of links', 'Paralelo': 'Parallel',
    'Pega la URL de un video, playlist o canal (o varias URLs a la vez)': 'Paste the URL of a video, playlist or channel (or several URLs at once)',
    'Pegar desde el portapapeles': 'Paste from clipboard', 'Importar URLs desde un .txt': 'Import URLs from a .txt',
    'Abrir la carpeta de descargas': 'Open the downloads folder', 'Suelta el enlace para analizarlo': 'Drop the link to analyze it',
    // Inicio y metadatos
    'Pega un enlace para empezar': 'Paste a link to get started',
    'Videos, playlists y canales de YouTube y de cientos de sitios más. También puedes pegar varias URLs a la vez o importar un .txt.':
      'Videos, playlists and channels from YouTube and hundreds of other sites. You can also paste several URLs at once or import a .txt.',
    'Pega la URL y pulsa Analizar': 'Paste the URL and press Analyze', 'Deja Auto o elige el formato': 'Keep Auto or pick the format',
    'Descarga, en paralelo y sin límite': 'Download, in parallel and without limits', 'No se pudo analizar': 'Could not analyze',
    'Cada enlace se descargará con la opción recomendada según tus preferencias.': 'Each link will be downloaded with the recommended option for your preferences.',
    'Importados o pegados': 'Imported or pasted', 'EN VIVO': 'LIVE',
    'Ya descargado antes (se saltará con "No repetir descargas")': 'Already downloaded (skipped with "Don\'t repeat downloads")',
    // Menús de preferencias
    'Preferencias de formato': 'Format preferences', 'Selección de formato': 'Format selection', 'Personalizado': 'Custom',
    'Códec de video': 'Video codec', 'El más eficiente disponible (AV1 › VP9 › H.264)': 'The most efficient available (AV1 › VP9 › H.264)',
    'Máxima compatibilidad': 'Maximum compatibility', 'Si el video no viene así, se convierte con la GPU': 'If the video isn\'t in this codec, it is converted with the GPU',
    'El que menos pesa': 'The smallest one', 'Buena eficiencia, muy común en YouTube': 'Good efficiency, very common on YouTube',
    'Resolución máxima': 'Maximum resolution', 'Según el criterio automático': 'Based on the Auto criterion',
    'Contenedor': 'Container', 'MP4 si los códecs lo permiten; si no, MKV': 'MP4 if the codecs allow it; otherwise MKV',
    'Se abre en cualquier reproductor': 'Plays in any player', 'Admite cualquier códec y varias pistas': 'Supports any codec and multiple tracks',
    'Solo VP9/AV1 con Opus': 'Only VP9/AV1 with Opus', 'Con audio': 'With audio', 'La mejor pista automáticamente': 'The best track automatically',
    'Sin audio': 'No audio', 'Solo la imagen': 'Video only', 'Elige la pista o la calidad del audio': 'Pick the audio track or quality',
    'Metadatos y extras': 'Metadata and extras', 'Idioma de la pista de audio': 'Audio track language', 'Subtítulos': 'Subtitles',
    'Recortar el video': 'Trim the video', 'Quitar anuncios (SponsorBlock)': 'Remove ads (SponsorBlock)', 'Formato de audio': 'Audio format',
    'Sin recodificar (Opus o M4A según la fuente)': 'No re-encoding (Opus or M4A depending on the source)', 'Compatible con todo': 'Works everywhere',
    'AAC, ideal para móviles y Apple': 'AAC, great for phones and Apple', 'El más eficiente': 'The most efficient', 'Sin pérdida (más pesado)': 'Lossless (larger)',
    'Menor tamaño sin perder calidad': 'Smallest size without losing quality', 'Menor tamaño (sacrifica calidad)': 'Smallest size (lower quality)',
    'Mejor calidad': 'Best quality', 'Máxima resolución con el códec más eficiente': 'Highest resolution with the most efficient codec',
    'Hasta 720p, menos fps y audio medio': 'Up to 720p, fewer fps and medium audio', 'El mayor bitrate disponible, sin mirar el tamaño': 'The highest bitrate available, regardless of size',
    'Elige tú el formato de la lista': 'Pick the format from the list yourself', 'En playlists cada video usa Auto': 'In playlists each video uses Auto',
    'Formato': 'Format', 'Códec': 'Codec', 'Resolución': 'Resolution', 'Idioma audio': 'Audio language', 'Original': 'Original',
    'Extras': 'Extras', 'Ninguno': 'None', 'Ninguna': 'None', 'Recortar': 'Trim', 'Entero': 'Whole', 'Quitar anuncios': 'Remove ads', 'Sí': 'Yes', 'No': 'No',
    'Buscando…': 'Searching…', 'Tamaño desconocido': 'Unknown size', 'sin recodificar': 'no re-encoding',
    'Equilibrado': 'Balanced', 'Ahorro': 'Saver', 'Máxima calidad': 'Best quality', 'Mejor códec': 'Best codec', 'Menor tamaño': 'Smallest',
    'Mayor bitrate': 'Highest bitrate', 'Idioma original': 'Original language', 'Sin recodificar': 'No re-encoding',
    'Calidad del audio': 'Audio quality', 'Alta (~130 kbps)': 'High (~130 kbps)', 'Media (~70 kbps)': 'Medium (~70 kbps)', 'Baja (~50 kbps)': 'Low (~50 kbps)',
    'Pista de audio': 'Audio track', 'Cancelar': 'Cancel', 'Elige un formato': 'Pick a format',
    'Videos de la playlist': 'Playlist videos', 'Enlaces': 'Links', 'Desmarcar todos': 'Unselect all', 'Marcar todos': 'Select all',
    'Ya descargado': 'Already downloaded', 'Automático para cada video': 'Automatic for each video',
    'Cada video se descarga con su opción recomendada según tus preferencias.': 'Each video is downloaded with its recommended option for your preferences.',
    'Sin opción recomendada': 'No recommended option', 'No hay formatos de este tipo para este enlace.': 'There are no formats of this type for this link.',
    'Opciones manuales': 'Manual options', 'Ocultar': 'Hide',
    'Título, autor, fecha y capítulos dentro del archivo': 'Title, author, date and chapters inside the file', 'Portada incrustada': 'Embedded cover',
    'Miniatura incrustada': 'Embedded thumbnail', 'Necesita los metadatos activados': 'Requires metadata to be on', 'Incrustar subtítulos': 'Embed subtitles',
    'Se meten dentro del video (puedes activarlos o no al verlo)': 'They go inside the video (you can turn them on or off while watching)',
    'Incluir automáticos': 'Include auto-generated', 'Este video no tiene subtítulos automáticos': 'This video has no auto-generated subtitles',
    'Si no hay manuales en ese idioma, usa los generados por YouTube': 'If there are no manual ones in that language, use YouTube\'s auto-generated',
    'Idiomas de este video': 'Languages in this video', 'Idiomas': 'Languages', 'Quitar anuncios de este video': 'Remove ads from this video',
    'Usa SponsorBlock (YouTube). Solo se consulta si lo activas.': 'Uses SponsorBlock (YouTube). It is only queried if you turn it on.',
    'Qué se quita': 'What gets removed', 'El idioma en que se grabó el video': 'The language the video was recorded in',
    'Desde': 'From', 'Hasta': 'To', 'Video entero': 'Whole video', 'Aplicar': 'Apply',
    'Patrocinio': 'Sponsor', 'Publicidad pagada dentro del video': 'Paid promotion inside the video', 'Autopromoción': 'Self-promotion',
    'Merch, Patreon, otros canales del creador': 'Merch, Patreon, the creator\'s other channels', 'Recordatorio de suscripción': 'Subscribe reminder',
    '"Dale like y suscríbete"': '"Like and subscribe"', 'Intro': 'Intro', 'Animación o cuenta atrás inicial': 'Opening animation or countdown',
    'Cierre': 'Outro', 'Créditos y pantallas finales': 'Credits and end screens', 'Avance': 'Preview', 'Resumen de lo que viene o lo que pasó': 'Recap or preview',
    'Parte sin música': 'Non-music section', 'En videos musicales, lo que no es la canción': 'In music videos, everything that isn\'t the song',
    'Relleno': 'Filler', 'Bromas o desvíos que no aportan al tema': 'Jokes or tangents that don\'t add to the topic',
    'Buscando segmentos en SponsorBlock…': 'Looking for segments on SponsorBlock…',
    'SponsorBlock no tiene segmentos marcados en este video: se descargará entero.': 'SponsorBlock has no segments marked for this video: it will be downloaded whole.',
    // Avisos
    'Pega una URL primero.': 'Paste a URL first.', 'Ver cola': 'View queue', 'Escribe el tiempo como m:ss, por ejemplo 1:20.': 'Write the time as m:ss, for example 1:20.',
    '"Hasta" tiene que ser mayor que "Desde".': '"To" must be greater than "From".', 'No se encontró el archivo (¿lo moviste o borraste?).': 'File not found (did you move or delete it?).',
    'El portapapeles está vacío.': 'The clipboard is empty.', 'Detección de GPU actualizada.': 'GPU detection updated.',
    'Se usará la versión incluida al reiniciar.': 'The bundled version will be used after restarting.',
    'Registro de descargas borrado: ya no se saltará ningún video.': 'Download record cleared: no video will be skipped.',
    'Eso no parece un enlace (debe empezar por http).': 'That doesn\'t look like a link (it must start with http).',
    'ffmpeg descargado e instalado.': 'ffmpeg downloaded and installed.', 'aria2 descargado e instalado.': 'aria2 downloaded and installed.',
    'Reiniciar ahora': 'Restart now', 'Vacío: no se añade nada.': 'Empty: nothing is added.', 'sin cambios respecto a lo normal': 'no changes from the defaults',
    // Cola
    'En cola': 'Queued', 'Iniciando': 'Starting', 'Descargando': 'Downloading', 'Procesando': 'Processing', 'Esperando turno': 'Waiting for its turn',
    'Convirtiendo': 'Converting', 'Completado': 'Completed', 'Error': 'Error', 'Cancelado': 'Cancelled', 'Reintentando': 'Retrying', 'En pausa': 'Paused',
    'Abrir archivo': 'Open file', 'Mostrar en la carpeta': 'Show in folder', 'Quitar de la lista': 'Remove from list', 'Continuar': 'Resume',
    'Reintentar': 'Retry', 'Cola en pausa': 'Queue paused', 'Se continuará desde donde se quedó': 'It will resume where it left off',
    'Ya estaba en el registro de descargas': 'It was already in the download record', 'con aria2': 'with aria2', 'Reanudar': 'Resume', 'Pausar': 'Pause',
    'La cola está vacía': 'The queue is empty', 'Analiza un video o una playlist y pulsa Descargar.': 'Analyze a video or playlist and press Download.',
    'Descargas paralelas': 'Parallel downloads', 'Sin límite': 'No limit', 'Velocidad': 'Speed', 'Abrir carpeta': 'Open folder',
    'Limpiar terminadas': 'Clear finished', 'Cancelar todo': 'Cancel all', 'Desactivado: de una en una': 'Off: one at a time',
    'Preparando': 'Preparing', 'Uniendo video y audio': 'Merging video and audio', 'Extrayendo audio': 'Extracting audio',
    'Añadiendo metadatos': 'Adding metadata', 'Incrustando miniatura': 'Embedding thumbnail', 'Incrustando subtítulos': 'Embedding subtitles',
    'Reparando contenedor': 'Fixing container', 'Buscando anuncios (SponsorBlock)': 'Looking for ads (SponsorBlock)', 'Quitando anuncios': 'Removing ads',
    'Esperando turno para convertir': 'Waiting to convert', 'Retomado tras cerrar la app': 'Resumed after closing the app',
    'aria2 no está instalado (Ajustes → Red); se usó yt-dlp.': 'aria2 is not installed (Settings → Network); yt-dlp was used.',
    // Ajustes
    'Descargas': 'Downloads', 'Carpeta de destino': 'Destination folder', 'Cambiar': 'Change', 'Opción recomendada automática': 'Automatic recommended option',
    'Muestra siempre una opción recomendada (Auto). Si la apagas, eliges a mano de la lista.': 'Always shows a recommended option (Auto). If you turn it off, you pick from the list.',
    'Criterio de la recomendación': 'Recommendation criterion', 'Se recuerda el último que uses en Descargar.': 'The last one you use in Download is remembered.',
    'Subcarpeta por playlist': 'Subfolder per playlist', 'Guarda cada playlist en una carpeta con su nombre.': 'Saves each playlist in a folder with its name.',
    'Nombre de archivo': 'File name', 'Plantilla de yt-dlp, p. ej.': 'yt-dlp template, e.g.', 'o': 'or',
    'Idiomas de subtítulos por defecto': 'Default subtitle languages',
    'Separados por comas. Se usan en playlists y cuando no eliges otros en Descargar.': 'Comma-separated. Used for playlists and when you don\'t pick others in Download.',
    'Numerar los archivos de una playlist': 'Number playlist files', 'Añade el orden al nombre:': 'Adds the order to the name:',
    'No repetir descargas': 'Don\'t repeat downloads', 'Recuerda lo que ya bajaste y lo salta (útil para canales que vas actualizando).':
      'Remembers what you already downloaded and skips it (useful for channels you keep updating).',
    'Olvidar': 'Forget', 'Borrar el registro de descargas': 'Clear the download record', 'Retomar descargas al reabrir': 'Resume downloads on reopen',
    'Si cierras la app a mitad, al volver a abrirla continúa donde se quedó. Apagado: se cancelan al cerrar.':
      'If you close the app midway, it continues where it left off when reopened. Off: they are cancelled on close.',
    'Red y velocidad': 'Network and speed', 'Límite de velocidad': 'Speed limit',
    'Total, repartido entre todas las descargas, para no saturar tu internet.': 'Total, shared among all downloads, so your internet isn\'t saturated.',
    'Personalizado…': 'Custom…', 'Reintentos automáticos': 'Automatic retries',
    'Si una descarga falla por la red o el servidor, se reintenta sola (espera 5 s, 15 s, 45 s…). 0 = no reintentar.':
      'If a download fails because of the network or server, it retries on its own (waits 5 s, 15 s, 45 s…). 0 = don\'t retry.',
    'Motor de descarga': 'Download engine',
    'aria2 abre varias conexiones por archivo. yt-dlp sigue analizando la página: aria2 no arregla errores de análisis.':
      'aria2 opens several connections per file. yt-dlp still analyzes the page: aria2 doesn\'t fix analysis errors.',
    'yt-dlp (nativo)': 'yt-dlp (native)', 'Auto (aria2 si falla yt-dlp)': 'Auto (aria2 if yt-dlp fails)', 'Elegir…': 'Choose…',
    'Descargas en paralelo': 'Parallel downloads', 'Activar descargas en paralelo': 'Enable parallel downloads',
    'Si está apagado, se descarga un video detrás de otro.': 'When off, videos are downloaded one after another.', 'Máximo a la vez': 'Maximum at once',
    '0 = sin límite (todos los videos de la cola a la vez).': '0 = no limit (every video in the queue at once).',
    'Fragmentos simultáneos por video': 'Simultaneous fragments per video', 'Acelera videos troceados (HLS/DASH). Recomendado: 4.': 'Speeds up fragmented videos (HLS/DASH). Recommended: 4.',
    'Conversiones simultáneas': 'Simultaneous conversions', 'Cuántos videos se recodifican a la vez con ffmpeg (para no saturar la GPU).':
      'How many videos are re-encoded at once with ffmpeg (so the GPU isn\'t saturated).',
    'Aceleración por hardware': 'Hardware acceleration', 'Codificador para H.265 / H.264': 'Encoder for H.265 / H.264', 'Detectando…': 'Detecting…',
    'Auto (mejor GPU disponible)': 'Auto (best GPU available)', 'Desactivado (CPU)': 'Off (CPU)', 'Decodificar con la GPU': 'Decode with the GPU',
    'Usa': 'Uses', 'al leer el video original.': 'when reading the original video.', 'Calidad de conversión': 'Conversion quality',
    'Menor = mejor calidad y más tamaño.': 'Lower = better quality and larger size.', '(CPU usa CRF': '(CPU uses CRF',
    'Volver a detectar': 'Detect again', 'Por si cambiaste de controlador o de ffmpeg.': 'In case you changed drivers or ffmpeg.', 'Detectar': 'Detect',
    'Cookies': 'Cookies', 'Origen de las cookies': 'Cookie source',
    'Para videos privados, con restricción de edad o si YouTube pide iniciar sesión.': 'For private or age-restricted videos, or if YouTube asks you to sign in.',
    'Archivo': 'File', 'Navegador': 'Browser', 'Archivo cookies.txt': 'cookies.txt file', 'Debe estar cerrado mientras se leen las cookies.': 'It must be closed while the cookies are read.',
    'El archivo se normaliza en una copia temporal que se borra al terminar cada descarga. La app solo guarda la':
      'The file is normalized into a temporary copy that is deleted after each download. The app only stores the',
    'ruta': 'path', ', nunca el contenido de las cookies. En Windows, Chrome y Edge cifran sus cookies y suelen fallar: usa Firefox o exporta un':
      ', never the cookie contents. On Windows, Chrome and Edge encrypt their cookies and often fail: use Firefox or export a',
    'Herramientas': 'Tools', 'Runtime de JavaScript': 'JavaScript runtime', 'Canal de actualización': 'Update channel', 'Estable': 'Stable',
    'Actualizar yt-dlp': 'Update yt-dlp', 'Cuando YouTube cambia, se arregla actualizando yt-dlp; no hace falta reinstalar la app.':
      'When YouTube changes, updating yt-dlp fixes it; no need to reinstall the app.', 'Reiniciar': 'Restart', 'Usar la incluida': 'Use the bundled one',
    'Buscar actualizaciones al abrir': 'Check for updates on launch',
    'Como mucho una vez al día, en segundo plano. Nightly trae los arreglos antes, pero está menos probada.':
      'At most once a day, in the background. Nightly gets fixes sooner, but is less tested.', 'Versiones': 'Versions',
    'Las preferencias de formato (códec, resolución, audio, metadatos…) se recuerdan solas cada vez que descargas.':
      'Format preferences (codec, resolution, audio, metadata…) are remembered automatically every time you download.',
    'Ventana, avisos y apariencia': 'Window, notifications and appearance', 'Notificaciones de Windows': 'Windows notifications',
    'Aviso al terminar, con botón para abrir la carpeta.': 'Notification when finished, with a button to open the folder.',
    'Al terminar cada playlist o lote': 'When each playlist or batch finishes', 'Por cada video': 'For every video', 'Minimizar a la bandeja': 'Minimize to tray',
    'Al minimizar, la ventana se oculta junto al reloj y las descargas siguen. La X cierra la app.':
      'When minimized, the window hides next to the clock and downloads continue. The X closes the app.',
    'Tema': 'Theme', 'Oscuro': 'Dark', 'Claro': 'Light', 'Sistema': 'System', 'Idioma': 'Language', 'Automático (del sistema)': 'Automatic (system)',
    'Avanzado': 'Advanced', 'Corte exacto': 'Exact cut',
    'Al recortar o quitar anuncios, corta en el fotograma exacto (recodifica los bordes, más lento). Apagado: corta en el fotograma clave más cercano.':
      'When trimming or removing ads, cuts at the exact frame (re-encodes the edges, slower). Off: cuts at the nearest keyframe.',
    'Suplantar navegador (impersonation)': 'Impersonate browser (impersonation)',
    'Hace que las peticiones parezcan venir de Chrome. Ayuda con sitios que bloquean descargas con errores 403/410. Requiere el componente curl_cffi.':
      'Makes requests look like they come from Chrome. Helps with sites that block downloads with 403/410 errors. Requires the curl_cffi component.',
    'Falta el componente curl_cffi.': 'The curl_cffi component is missing.',
    'La versión de yt-dlp en uso no admite suplantar a Chrome.': "The yt-dlp version in use doesn't support impersonating Chrome.",
    'Comando personalizado': 'Custom command', 'Argumentos extra de yt-dlp, como en la consola. Ej.:': 'Extra yt-dlp arguments, like in the console. E.g.:',
    '. Por seguridad no se permiten opciones que ejecutan programas.': '. For safety, options that run programs are not allowed.', 'Probar': 'Test',
    'Ninguno ': 'None', 'ffmpeg listo': 'ffmpeg ready', 'Falta ffmpeg': 'ffmpeg missing', 'GPU desactivada (CPU)': 'GPU off (CPU)',
    'Detectando GPU…': 'Detecting GPU…', 'Sin GPU compatible: CPU': 'No compatible GPU: CPU', 'Paralelo: sin límite': 'Parallel: no limit',
    'Paralelo desactivado': 'Parallel off', 'No se detectó GPU compatible; se usará la CPU.': 'No compatible GPU found; the CPU will be used.',
    'No encontrado': 'Not found', 'Extrayendo': 'Extracting', 'Reinstalar': 'Reinstall', 'incluida en la app': 'bundled with the app',
    'la versión descargada falló al cargar': 'the downloaded version failed to load', 'Buscando la última versión…': 'Looking for the latest version…',
    'No encontrado. Instala Node.js o Deno para que YouTube muestre todos los formatos.': 'Not found. Install Node.js or Deno so YouTube shows every format.',
    // Errores (vienen del motor en español)
    'YouTube pide iniciar sesión para confirmar que no eres un bot. Configura cookies en Ajustes.': 'YouTube asks you to sign in to confirm you\'re not a bot. Set up cookies in Settings.',
    'Video con restricción de edad: configura cookies de una cuenta en Ajustes.': 'Age-restricted video: set up cookies from an account in Settings.',
    'El video es privado.': 'The video is private.', 'Video solo para miembros: necesitas cookies de una cuenta con acceso.': 'Members-only video: you need cookies from an account with access.',
    'El video no está disponible.': 'The video is not available.', 'La playlist no existe o es privada.': 'The playlist doesn\'t exist or is private.',
    'Esta URL no es compatible.': 'This URL is not supported.', 'El formato elegido ya no está disponible. Prueba con Auto.': 'The chosen format is no longer available. Try Auto.',
    'Falta ffmpeg. Descárgalo desde Ajustes → Herramientas.': 'ffmpeg is missing. Download it from Settings → Tools.',
    'No se pudieron leer las cookies del navegador (ciérralo o usa un archivo cookies.txt).': 'Couldn\'t read the browser cookies (close it or use a cookies.txt file).',
    'No se pudieron descifrar las cookies del navegador. Usa Firefox o un archivo cookies.txt.': 'Couldn\'t decrypt the browser cookies. Use Firefox or a cookies.txt file.',
    'El servidor rechazó la descarga (403). Prueba con cookies o actualiza la app.': 'The server rejected the download (403). Try cookies or update yt-dlp.',
    'Demasiadas peticiones (429). Espera un poco o usa cookies.': 'Too many requests (429). Wait a bit or use cookies.',
    'El servidor tuvo un error temporal (5xx).': 'The server had a temporary error (5xx).', 'La conexión tardó demasiado en responder.': 'The connection took too long to respond.',
    'Se cortó la conexión con el servidor.': 'The connection to the server was cut.', 'Sin conexión a internet (no se pudo resolver el servidor).': 'No internet connection (couldn\'t resolve the server).',
    'Error de red al conectar con el servidor.': 'Network error connecting to the server.', 'La descarga se interrumpió a mitad.': 'The download was interrupted midway.',
    'Falló la descarga de un fragmento del video.': 'A video fragment failed to download.', 'El servidor dejó de enviar datos.': 'The server stopped sending data.',
    'aria2 no pudo completar la descarga.': 'aria2 couldn\'t complete the download.', 'Error desconocido': 'Unknown error',
    'No se puede descargar: error 410. La página no se descargó desde el servidor. Probablemente lo bloqueó por no coincidir el hash del video.':
      'Can\'t download: error 410. The page wasn\'t served by the server. It was probably blocked because the video hash didn\'t match.',
    'Pega una URL válida (debe empezar por http).': 'Paste a valid URL (it must start with http).', 'El análisis caducó; vuelve a analizar la URL.': 'The analysis expired; analyze the URL again.',
    'No hay nada seleccionado para descargar.': 'Nothing is selected to download.',
    'Hay descargas en curso: espera a que terminen o cancélalas antes de reiniciar.': 'There are downloads in progress: wait for them to finish or cancel them before restarting.',
    'Ese archivo no es ffmpeg.exe; se mantiene la ruta anterior.': 'That file isn\'t ffmpeg.exe; the previous path is kept.',
    'Ese archivo no es aria2c.exe; se mantiene la ruta anterior.': 'That file isn\'t aria2c.exe; the previous path is kept.',
    'No pongas URLs aquí: solo argumentos.': 'Don\'t put URLs here: only arguments.', 'No se permiten postprocesadores que ejecutan programas.': 'Postprocessors that run programs are not allowed.',
    'La playlist está vacía o no se pudieron leer sus videos.': 'The playlist is empty or its videos couldn\'t be read.',
    // Avisos de seguridad y torrents
    'Aviso de seguridad': 'Security notice', 'No volver a mostrar este aviso': 'Don\'t show this again', 'Seguir': 'Continue',
    'Vas a descargar un torrent (P2P)': 'You are about to download a torrent (P2P)',
    'El contenido lo comparten desconocidos: puede traer malware. No abras programas (.exe, .bat…) que vengan dentro.':
      'The content is shared by strangers and may contain malware. Don\'t open programs (.exe, .bat…) that come inside.',
    'Mientras se descarga, tu IP es visible para los demás participantes y se suben fragmentos (limitado en Ajustes).':
      'While downloading, your IP is visible to other peers and pieces are uploaded (limited in Settings).',
    'Al terminar, JabsDLP deja de compartir al instante (sin seed).': 'When finished, JabsDLP stops sharing immediately (no seeding).',
    'Descarga solo contenido que tengas derecho a descargar.': 'Only download content you have the right to download.',
    'Conexión sin cifrar (http://)': 'Unencrypted connection (http://)',
    'Alguien en tu red podría ver lo que descargas o modificar el archivo por el camino.': 'Someone on your network could see what you download or tamper with the file in transit.',
    'Si existe, usa la versión https:// del enlace.': 'If available, use the https:// version of the link.', 'Sitio no reconocido': 'Unrecognized site',
    'yt-dlp no tiene soporte específico para esta web y usa su extractor genérico.': 'yt-dlp has no specific support for this site and uses its generic extractor.',
    'Asegúrate de que confías en la página antes de descargar.': 'Make sure you trust the page before downloading.',
    'El enlace apunta a un programa o archivo comprimido': 'The link points to a program or archive',
    'Los ejecutables y comprimidos pueden contener software malicioso.': 'Executables and archives may contain malicious software.',
    'JabsDLP nunca los abre directamente: solo te los muestra en su carpeta.': 'JabsDLP never opens them directly: it only shows them in their folder.',
    'Motor aria2': 'aria2 engine',
    'aria2 solo se usa en descargas directas (http/ftp). Los streams HLS y DASH siempre van con el motor nativo de yt-dlp.':
      'aria2 is only used for direct downloads (http/ftp). HLS and DASH streams always use yt-dlp\'s native engine.',
    'Así se evita la vulnerabilidad CVE-2026-50574 (inyección de opciones en aria2c desde manifiestos DASH), ya corregida en el yt-dlp que trae la app.':
      'This avoids CVE-2026-50574 (aria2c option injection from DASH manifests), already fixed in the yt-dlp bundled with the app.',
    'aria2 tampoco seguirá enlaces .torrent ni metalink que pueda devolver un servidor.': 'aria2 also won\'t follow .torrent or metalink links a server may return.',
    'Torrent': 'Torrent', 'Torrent / magnet · P2P': 'Torrent / magnet · P2P', 'Descargar torrent': 'Download torrent',
    'Fuente desconocida: revisa lo que descargas antes de abrirlo.': 'Unknown source: check what you download before opening it.',
    'Los torrents necesitan aria2. Instálalo en': 'Torrents need aria2. Install it in', 'Ajustes → Red y velocidad': 'Settings → Network and speed',
    'Los torrents necesitan aria2: instálalo en Ajustes → Red y velocidad.': 'Torrents need aria2: install it in Settings → Network and speed.',
    'No es un enlace magnet ni un archivo .torrent.': 'It isn\'t a magnet link or a .torrent file.', 'Torrent · sin seed': 'Torrent · no seeding',
    'Conectando con los pares': 'Connecting to peers', 'Descargando torrent': 'Downloading torrent', 'Completado (sin seed)': 'Completed (no seeding)',
    'Subida máxima en torrents': 'Maximum torrent upload',
    'KB/s que se comparten mientras se descarga un torrent. Al terminar nunca se sigue compartiendo (sin seed).':
      'KB/s shared while a torrent downloads. When finished it never keeps sharing (no seeding).',
    'Avisos de seguridad': 'Security notices', 'Torrents, conexiones sin cifrar, sitios no reconocidos y archivos ejecutables.':
      'Torrents, unencrypted connections, unrecognized sites and executable files.', 'Volver a mostrarlos': 'Show them again',
    'Los avisos de seguridad se volverán a mostrar.': 'Security notices will be shown again.',
    'Por seguridad no se abre directamente: no es un archivo multimedia. Se muestra en su carpeta.':
      'For safety it isn\'t opened directly: it isn\'t a media file. It is shown in its folder.',
    'Se descarga con aria2, con la subida limitada a': 'Downloaded with aria2, with upload limited to', 'KB/s y': 'KB/s and', 'sin seed': 'no seeding',
    ': al terminar deja de compartir.': ': it stops sharing when finished.',
    'Desinstalar': 'Uninstall', 'aria2 desinstalado. El motor vuelve a ser yt-dlp.': 'aria2 uninstalled. The engine is yt-dlp again.',
    'Hay descargas usando aria2: espera a que terminen o cancélalas.': 'Some downloads are using aria2: wait for them to finish or cancel them.',
  };

  const MESES = { ene: 'Jan', feb: 'Feb', mar: 'Mar', abr: 'Apr', may: 'May', jun: 'Jun', jul: 'Jul', ago: 'Aug', sep: 'Sep', oct: 'Oct', nov: 'Nov', dic: 'Dec' };
  const tr = s => EN[s] || s;
  const PATRONES = [
    [/^(\d+) enlaces$/, m => `${m[1]} links`], [/^(\d+) videos?$/, m => `${m[1]} video${m[1] === '1' ? '' : 's'}`],
    [/^Extraído de (.+)$/, m => `From ${m[1] === 'la web' ? 'the web' : m[1]}`],
    [/^(\d{2}) (ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic) (\d{4})$/, m => `${MESES[m[2]]} ${m[1]}, ${m[3]}`],
    [/^convierte a (.+)$/, m => `converts to ${m[1]}`], [/^Se convertirá a (.+) con (.+)$/, m => `Will be converted to ${m[1]} with ${m[2]}`],
    [/^Si un video no viene en (.+), se convierte con (.+)$/, m => `If a video isn't in ${m[1]}, it's converted with ${m[2]}`],
    [/^Metadatos \+(\d+)$/, m => `Metadata +${m[1]}`], [/^Descargar (\d+) videos?$/, m => `Download ${m[1]} video${m[1] === '1' ? '' : 's'}`],
    [/^\((\d+) de (\d+)\)$/, m => `(${m[1]} of ${m[2]})`], [/^Ver opciones manuales \((\d+)\)$/, m => `Show manual options (${m[1]})`],
    [/^(\d+) segmentos? · (.+) que se quitarán$/, m => `${m[1]} segment${m[1] === '1' ? '' : 's'} · ${m[2]} will be removed`],
    [/^Formato m:ss o h:mm:ss\. Duración: (.+)\. Se descarga el video y se recorta en tu equipo\.$/, m => `Format m:ss or h:mm:ss. Length: ${m[1]}. The video is downloaded and trimmed on your computer.`],
    [/^Con un recorte no se quitan anuncios/, () => 'Ads aren\'t removed when trimming (the times would no longer match).'],
    [/^Recortando el tramo$/, () => 'Trimming the clip'],
    [/^El video dura (.+)\.$/, m => `The video is ${m[1]} long.`], [/^(\d+) (descarga añadida|descargas añadidas) a la cola\.$/, m => `${m[1]} download${m[1] === '1' ? '' : 's'} added to the queue.`],
    [/^(\d+) URLs importadas\.$/, m => `${m[1]} URLs imported.`], [/^No se pudo descargar ffmpeg: (.+)$/, m => `Couldn't download ffmpeg: ${m[1]}`],
    [/^No se pudo descargar aria2: (.+)$/, m => `Couldn't download aria2: ${m[1]}`],
    [/^en (\d+) h (\d+) min$/, m => `in ${m[1]} h ${m[2]} min`], [/^en (\d+) min (\d+) s$/, m => `in ${m[1]} min ${m[2]} s`],
    [/^en (\d+) s$/, m => `in ${m[1]} s`],
    [/^aria2 de JabsDLP desinstalado\. Sigue habiendo otro aria2 en tu equipo: (.+)$/, m => `JabsDLP's aria2 uninstalled. There's still another aria2 on your computer: ${m[1]}`],
    [/^No se pudo borrar aria2: (.+)$/, m => `Couldn't delete aria2: ${m[1]}`],
    [/^velocidad (.+)$/, m => `speed ${m[1]}`], [/^Convertido con (.+)$/, m => `Converted with ${m[1]}`],
    [/^Tras (\d+) reintentos?$/, m => `After ${m[1]} ${m[1] === '1' ? 'retry' : 'retries'}`],
    [/^Reintento (\d+) de (\d+) en (\d+) s$/, m => `Retry ${m[1]} of ${m[2]} in ${m[3]} s`], [/^Reintento (\d+) de (\d+)$/, m => `Retry ${m[1]} of ${m[2]}`],
    [/^Reintento (\d+)( con aria2)?$/, m => `Retry ${m[1]}${m[2] ? ' with aria2' : ''}`],
    [/^(\d+) activas$/, m => `${m[1]} active`], [/^(\d+) en cola$/, m => `${m[1]} queued`], [/^(\d+) completadas$/, m => `${m[1]} completed`],
    [/^(\d+) ya descargadas$/, m => `${m[1]} already downloaded`], [/^(\d+) con error$/, m => `${m[1]} failed`],
    [/^Hasta (\d+) a la vez$/, m => `Up to ${m[1]} at once`], [/^Máx\. (.+) MB\/s en total$/, m => `Max ${m[1]} MB/s in total`],
    [/^Paralelo: máx\. (\d+)$/, m => `Parallel: max ${m[1]}`], [/^Detectado: (.+)\. En Auto se usa (.+)\.$/, m => `Detected: ${m[1]}. Auto uses ${m[2]}.`],
    [/^No instalado \(versión (.+) disponible\)$/, m => `Not installed (version ${m[1]} available)`],
    [/^Encontrado: (.+) \(necesario para YouTube\)\.$/, m => `Found: ${m[1]} (needed for YouTube).`],
    [/^En uso: (.+)$/, m => `In use: ${m[1]}`], [/^descargada \((nightly|estable)\)$/, m => `downloaded (${m[1] === 'estable' ? 'stable' : 'nightly'})`],
    [/^Motivo: (.+)$/, m => `Reason: ${m[1]}`],
    [/^yt-dlp (.+) \(incluida (.+)\)$/, m => `yt-dlp ${m[1]} (bundled ${m[2]})`], [/^Descargando yt-dlp (.+)…$/, m => `Downloading yt-dlp ${m[1]}…`],
    [/^yt-dlp (.+) descargado; reinicia para usarlo\.$/, m => `yt-dlp ${m[1]} downloaded; restart to use it.`],
    [/^yt-dlp (.+) ya está descargado(\.|; reinicia para usarlo\.)$/, m => `yt-dlp ${m[1]} is already downloaded${m[2] === '.' ? '.' : '; restart to use it.'}`],
    [/^Ya tienes la última versión (estable|nightly) \((.+), incluida en la app\)\.( Reinicia para volver a ella\.)?$/,
      m => `You already have the latest ${m[1] === 'estable' ? 'stable' : 'nightly'} version (${m[2]}, bundled with the app).${m[3] ? ' Restart to switch back to it.' : ''}`],
    [/^No se pudo actualizar yt-dlp: (.+)$/, m => `Couldn't update yt-dlp: ${m[1]}`],
    [/^Correcto: (.+)$/, m => `OK: ${tr(m[1])}`], [/^Descargando (video|audio) \((\d+)\/(\d+)\)$/, m => `Downloading ${m[1]} (${m[2]}/${m[3]})`],
    [/^Convirtiendo a (.+)$/, m => `Converting to ${m[1]}`], [/^La GPU \((.+)\) falló al convertir; se usó la CPU\.$/, m => `The GPU (${m[1]}) failed to convert; the CPU was used.`],
    [/^(.+) no está disponible en (\d+)p; se usa el mejor códec disponible\.$/, m => `${m[1]} isn't available at ${m[2]}p; the best available codec is used.`],
    [/^Este video no tiene audio en «(.+)»; se usa el idioma original\.$/, m => `This video has no audio in "${m[1]}"; the original language is used.`],
    [/^No se permiten por seguridad o porque la app ya los gestiona: (.+)$/, m => `Not allowed for safety or because the app already handles them: ${m[1]}`],
    [/^No se permiten estas opciones: (.+)$/, m => `These options are not allowed: ${m[1]}`], [/^Argumentos no válidos: (.+)$/, m => `Invalid arguments: ${m[1]}`],
    [/^Comillas sin cerrar: (.+)$/, m => `Unclosed quotes: ${m[1]}`], [/^No se pudo consultar SponsorBlock: (.+)$/, m => `Couldn't query SponsorBlock: ${m[1]}`],
    [/^No disponible: (.+)$/, m => `Not available: ${m[1]}`],
    [/^No se pudo aplicar --impersonate del comando personalizado: (.+)$/, m => `Couldn't apply --impersonate from the custom command: ${m[1]}`],
    [/^No se pudo activar la suplantación de navegador: (.+)$/, m => `Couldn't enable browser impersonation: ${m[1]}`],
    [/^No se pudo comprobar la disponibilidad de impersonation: (.+)$/, m => `Couldn't check impersonation availability: ${m[1]}`],
    // Genéricos al final (los específicos de arriba tienen prioridad)
    [/^(.+) en total$/, m => `${m[1]} in total`],
    [/^(.+) de (.+)$/, m => /\d/.test(m[1]) && /\d/.test(m[2]) && /B$/.test(m[2]) ? `${m[1]} of ${m[2]}` : null],
    [/^(.+) restantes$/, m => `${m[1]} left`],
  ];

  function traducir(texto) {
    const limpio = texto.trim();
    if (!limpio) return texto;
    let resultado = EN[limpio];
    if (resultado === undefined) {
      for (const [patron, fn] of PATRONES) {
        const m = limpio.match(patron);
        if (m) { const r = fn(m); if (r) { resultado = r; break; } }
      }
    }
    if (resultado === undefined && limpio.includes(' · ')) {
      const partes = limpio.split(' · ').map(p => traducirParte(p));
      if (partes.some((p, i) => p !== limpio.split(' · ')[i])) resultado = partes.join(' · ');
    }
    if (resultado === undefined) return texto;
    return texto.replace(limpio, resultado);
  }

  function traducirParte(p) {
    if (EN[p] !== undefined) return EN[p];
    for (const [patron, fn] of PATRONES) {
      const m = p.match(patron);
      if (m) { const r = fn(m); if (r) return r; }
    }
    return p;
  }

  const originales = new WeakMap();
  const ATRIBUTOS = ['title', 'placeholder'];
  const NO = 'SCRIPT,STYLE,TEXTAREA,CODE';

  function saltar(nodo) {
    const el = nodo.nodeType === 1 ? nodo : nodo.parentElement;
    return !el || el.closest('.no-traducir') || el.closest(NO);
  }

  function traducirNodo(nodo) {
    if (I18N.idioma !== 'en' || saltar(nodo)) return;
    if (nodo.nodeType === 3) {
      const actual = nodo.nodeValue;
      const nuevo = traducir(actual);
      if (nuevo !== actual) {
        originales.set(nodo, actual);
        nodo.nodeValue = nuevo;
      }
      return;
    }
    if (nodo.nodeType !== 1) return;
    for (const a of ATRIBUTOS) {
      const v = nodo.getAttribute(a);
      if (v) {
        const nuevo = traducir(v);
        if (nuevo !== v) { nodo.dataset[`orig_${a}`] = v; nodo.setAttribute(a, nuevo); }
      }
    }
    if (nodo.tagName === 'OPTION') return traducirTexto(nodo);
    nodo.childNodes.forEach(traducirNodo);
  }

  function traducirTexto(nodo) { nodo.childNodes.forEach(traducirNodo); }

  function restaurar(raiz) {
    const recorrer = document.createTreeWalker(raiz, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT);
    let n = recorrer.currentNode;
    while (n) {
      if (n.nodeType === 3 && originales.has(n)) { n.nodeValue = originales.get(n); originales.delete(n); }
      if (n.nodeType === 1) {
        for (const a of ATRIBUTOS) {
          const o = n.dataset?.[`orig_${a}`];
          if (o) { n.setAttribute(a, o); delete n.dataset[`orig_${a}`]; }
        }
      }
      n = recorrer.nextNode();
    }
  }

  const observador = new MutationObserver(cambios => {
    if (I18N.idioma !== 'en') return;
    for (const c of cambios) {
      if (c.type === 'characterData') traducirNodo(c.target);
      else if (c.type === 'attributes') traducirNodo(c.target);
      else c.addedNodes.forEach(traducirNodo);
    }
  });

  window.I18N = {
    idioma: 'es',
    traducir,
    cambiar(idioma) {
      this.idioma = idioma === 'en' ? 'en' : 'es';
      document.documentElement.lang = this.idioma;
      if (this.idioma === 'en') traducirNodo(document.body);
      else restaurar(document.body);
    },
  };
  // Traduce un texto suelto (para mensajes que se construyen fuera del DOM)
  window.t = s => (window.I18N.idioma === 'en' ? traducir(String(s)) : String(s));

  // El script va al final del <body>: se vigila desde ya (la app pinta antes de DOMContentLoaded)
  const vigilar = () => observador.observe(document.body, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ATRIBUTOS });
  if (document.body) vigilar(); else document.addEventListener('DOMContentLoaded', vigilar);
})();
