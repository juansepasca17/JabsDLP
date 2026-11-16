# Cambios de JabsDLP

Lo nuevo de cada versión, de la más reciente a la más antigua. Los `.exe` y los APK están en [Releases](https://github.com/juansepasca17/JabsDLP/releases).

## 1.7.9

- **Controles en la notificación** (Android, *Ajustes*, activado por defecto): lo que suena en Ver aparece en la
  notificación, en el panel de controles multimedia y en la pantalla de bloqueo, con su portada, la barra de tiempo y
  los botones anterior, pausa y siguiente (también responde a los botones de los auriculares). Sirve para música y
  para videos (con su miniatura).
- **Botón X** en la notificación, como en Spotify: pausa y la quita, y no vuelve a salir hasta que le des play en la
  app. En pausa también se puede quitar deslizándola.
- **Videos en segundo plano** (*Ajustes*): si sales de la app o apagas la pantalla, los videos **siguen sonando** (por
  defecto; antes Android los pausaba) y la lista pasa sola al siguiente, o **se pausan** si lo prefieres para ahorrar
  batería. La música siempre sigue sonando.

## 1.7.8

- **Portada de la música en el reproductor**: mientras suena un audio con portada, se ve nítida y centrada (como en
  las apps de música) sobre el fondo borroso. En *Ajustes* puedes elegir *Nítida sobre negro* o dejar *Solo fondo
  borroso* como antes.
- **Pasar al siguiente** (*Ajustes*, activado por defecto): al terminar un video o canción de una lista empieza el
  siguiente; apagado, se pausa al terminar.

## 1.7.7

- **Portadas en la lista de Ver**: al reproducir desde la Biblioteca, cada archivo muestra su portada en la lista (se
  cargan a medida que bajas) y, si es música, la portada de la que suena queda de fondo del reproductor.
- **Los controles del reproductor se esconden solos** a los pocos segundos también con música, como en YouTube: un
  toque los vuelve a mostrar y no se esconden mientras usas un botón.
- En inglés, el nombre de la lista ("170 files from the Library") ya sale traducido.

## 1.7.6

- **Biblioteca**:
  - **Iconos muy pequeños** (5 por fila en el celular) para ver muchos de un vistazo. En Android también se cambia
    el tamaño **pellizcando con dos dedos**, como en la Galería.
  - **Seleccionar todo** y, con lo seleccionado, **Reproducir** o **Aleatorio** (por ejemplo, escuchar una carpeta
    de música al azar), además de agruparlo en una playlist o añadirlo a una colección.
  - Los audios muestran su **portada** (la carátula incrustada) en lugar del icono de nota.
- **Portada y metadatos por separado**: en *Extras* puedes incrustar la portada (o la miniatura en los videos) sin los
  metadatos, o al revés. En audio, la portada es la miniatura del video y se ve en la Biblioteca y en tu
  reproductor de música.

## 1.7.5

- **Burbuja del portapapeles** (PC): además de *Descargar* (y *Al stack*), un botón **Ver** que abre el enlace en la
  pestaña Ver. También recuerda los atajos de Captura rápida, que funcionan con el enlace que acabas de copiar sin
  seleccionar nada: Ctrl + Alt + X para descargarlo y Ctrl + Alt + V para verlo.
- **El stack no se esconde**: si apagas el modo stack y tiene enlaces, su pestaña sigue en el borde derecho (más
  tenue) para que no se te olvide. Al tocarla (o con Ctrl + J) vuelve el modo stack con el panel abierto.

## 1.7.4

- **Log de la app** (*Ajustes → Avanzado → Guardar log de la app*, activado por defecto): anota lo que pasa (videos
  que abres en Ver y cuánto tardan en empezar, torrents, descargas y errores) para enviarlo si algo falla. Empieza uno
  nuevo cada vez que abres la app y guarda solo la sesión anterior; se puede apagar o borrar. En PC, *Abrir log*.
- **Guardar enlaces en colecciones sin analizarlos**: dentro de una colección, pega un enlace, magnet o `.torrent`
  (o usa el botón del portapapeles) y se añade al instante; el título, la miniatura y la duración se completan solos.
  En Descargar, el botón de colección junto a *Analizar* guarda el enlace que pegaste. Cada elemento dice qué es
  (video, playlist, torrent, enlace directo o archivo descargado). Los torrents se pueden guardar para verlos más tarde.
- **Carpetas de destino guardadas**: abajo en Descargar, el selector de la carpeta cambia a dónde va la descarga en un
  toque; con *＋ Añadir carpeta…* se guarda una nueva.
- **Atajo para ver un enlace** (PC, *Ajustes → Captura rápida*): selecciona un enlace en cualquier programa y pulsa
  Ctrl + Alt + V: se abre directo en la pestaña Ver. Se puede cambiar o apagar.
- **Atajos dentro de la app**: Ctrl + K abre o cierra Colecciones y Ctrl + J el stack. La lista completa está en
  *Ajustes → Ventana, avisos y apariencia → Atajos de teclado*.
- **Biblioteca**: mantén pulsado un archivo (con el dedo o el ratón) y desliza para seleccionar varios; tamaño de los
  iconos pequeño, mediano o grande (con iconos pequeños, tocar un archivo lo abre en Ver).
- **Ajustes**: botón propio y más grande para plegar cada sección; funciona aunque haya algo en el buscador, que
  tiene una X para borrarlo.
- Arreglado: en Android, entrar en una subcarpeta dentro de otra en la Biblioteca decía que la carpeta no existía.

## 1.7.3

- **Ver torrents en Android**: igual que en PC, se reproducen mientras se descargan, se puede saltar en la línea
  de tiempo y al cerrar no se sigue compartiendo (con [libtorrent4j](https://github.com/aldenml/libtorrent4j)).
- **Idioma del audio en todos los casos**: también en archivos con varias pistas de audio (un `.mkv` o `.mp4` con
  español e inglés) y en videos cuyo audio llega aparte (doblajes por DASH). Al cambiar de pista sigue en el mismo
  segundo.
- **Todos los subtítulos**: antes solo salían los primeros 12; ahora salen todos los del video y todas las
  traducciones automáticas de YouTube, con los nombres en tu idioma y un buscador en el menú. (YouTube a veces
  limita las traducciones automáticas: si una no carga, la app lo avisa.)
- **Calidad del video**: el menú muestra una opción por resolución (antes salían repetidas) y solo con formatos que
  tu equipo reproduce bien, así elegir una calidad ya no deja el video trabado.
- **Ver un solo video de una colección o del stack**: tocar un elemento lo reproduce solo; el botón *Ver* de la
  colección (o *Stack* en *Listas*) reproduce la lista entera.
- **Perfiles de descarga**: guarda tus preferencias de formato con un nombre («Solo audio MP3», «720p»…) y
  elígelas en Descargar, junto a *Preferencias de formato*; *Actual* son las que tengas puestas.
- **Biblioteca con subcarpetas**: el botón *Subcarpetas* muestra también los videos que hay dentro de las
  subcarpetas (cada uno dice en cuál está).
- **Comando personalizado**: tocar la plantilla elegida la quita.
- **Tamaño de los subtítulos** (*Ajustes → Ventana, avisos y apariencia*): pequeño, normal o grande. Por defecto
  son algo más grandes que antes, y más aún en pantalla completa.

## 1.7.2

- **Pestaña Ver:**
  - **Idioma del audio**: en videos con doblajes (YouTube) se elige sola la pista original, o si no la de tu idioma,
    y puedes cambiarla con el botón nuevo del reproductor.
  - Los **subtítulos automáticos** de YouTube ya no van a saltos (YouTube los manda por trozos y ahora se juntan).
  - Botón **X** para quitar el video y volver a la pantalla inicial.
  - Al cambiar de video, el nuevo empieza en 0:00 y el anterior deja de descargarse.
  - En pausa deja de pedir el video al rato, así que no gasta datos de más.
  - El **stack** se puede ver como lista de reproducción (en *Listas* o con el botón de cada elemento del stack).
  - Con *Mostrar log completo* activado, los errores de Ver muestran el detalle con **Copiar log**, como en la Cola.
- **Stack**: acepta también magnets, archivos `.torrent` y enlaces directos `.m3u8`/`.mpd`.
- **Biblioteca**: al marcar un archivo entras en modo selección: tocar cualquier otro lo marca, y
  *Quitar selección* lo desactiva.
- **Ajustes**: buscador arriba y secciones que se pliegan y despliegan (se recuerda cuáles dejaste plegadas).

## 1.7.1

- **Torrents en la pestaña Ver**: pega un magnet o un enlace `.torrent` (o pulsa **Ver sin descargar** en el panel
  de torrents de Descargar) y se reproduce mientras se descarga.
  - Solo se baja el video (el archivo más grande) y lo que estás viendo va primero, así que puedes saltar en la
    línea de tiempo.
  - Se ve en vivo cuántos pares hay, la velocidad y cuánto lleva descargado.
  - **Sin compartir al cerrar**: al cerrar el reproductor o salir de la pestaña, el torrent se quita y lo descargado
    se borra. Mientras se ve, la subida queda limitada (*Ajustes → Red → subida máxima en torrents*).
  - Antes de empezar se avisa de los riesgos del P2P.
  - Usa [libtorrent](https://www.libtorrent.org) 2.1.1 (BSD).

## 1.7.0

- **Pestaña Ver**: reproduce enlaces sin descargarlos, dentro de la app. Funciona con YouTube, enlaces `.m3u8` y cientos
  de sitios más, y con archivos de tu equipo.
  - Reproductor propio: línea de tiempo con lo ya cargado, volumen, velocidad (0,5×–2×), subtítulos, calidad
    (automática o fija) y pantalla completa.
  - Atajos: espacio/K, ←/→ (5 s), J/L (10 s), ↑/↓ (volumen), M, C (subtítulos), F, N/P (siguiente/anterior).
  - **Listas de reproducción con tus colecciones**: botón **Ver** en una colección. Incluye siguiente/anterior,
    reproducción automática, aleatorio y repetir.
  - **Continuar donde lo dejaste**: guarda el segundo exacto de cada video de una colección y marca los vistos con ✓.
  - **Vistos recientemente** y botón **Ver aquí** en la Cola y en la Biblioteca.
  - Archivos locales con códecs que el navegador no reproduce (por ejemplo, HEVC en `.mkv`) se convierten al vuelo.
- **Cómo funciona**: un pequeño servidor local (solo en `127.0.0.1` y con un token aleatorio) pide el video con las
  cabeceras correctas y se lo pasa al reproductor. Los streams HLS se reproducen con [hls.js](https://github.com/video-dev/hls.js)
  (Apache-2.0), incluido en la app con su SHA-256 verificado.

## 1.6.0

- **Modo stack**, activable con el chip **Stack** junto a Video/Playlist (apagado por defecto). Los enlaces que
  pegas se van sumando a una lista en vez de reemplazar el análisis:
  - cada video puede ir "como el resto", solo audio o con resolución máxima;
  - todo se descarga junto en una carpeta con el nombre que elijas;
  - el stack se guarda aunque cierres la app;
  - opcional: que cada enlace empiece a descargarse al momento.
- **Captura rápida** (*Ajustes → Captura rápida*, todo apagado por defecto):
  - **Atajo global** (Ctrl+Alt+X, Ctrl+Shift+X o Ctrl+Alt+D): selecciona un enlace en cualquier programa, pulsa el
    atajo y llega a JabsDLP (al stack, si está activo) sin copiar, pegar ni cambiar de ventana;
  - **Vigilar el portapapeles**: al copiar un enlace de un sitio que yt-dlp reconoce aparece una burbuja abajo a la
    derecha con **Al stack** / **Descargar**, sin quitarte el foco; o se añade sin preguntar, si lo prefieres. No
    aparece mientras juegas o ves algo a pantalla completa.
- **Colecciones**: grupos de enlaces y archivos para más tarde.
  - Se abren desde un botón en la barra lateral o, si lo eliges en Ajustes, uno flotante rojo abajo a la derecha.
  - Se reordenan arrastrando y se descargan enteras con un clic.
  - Se comparten exportándolas como archivo **.jabs** (o .txt); quien lo importa recibe los mismos enlaces.
  - **★ Favoritos** es una colección fija.
- **Biblioteca**: lo descargado, sin abrir el Explorador.
  - Miniaturas, búsqueda por nombre, filtros por tipo y fecha, y orden.
  - **★ favoritos**, selección múltiple y **Agrupar en playlist**.
  - Enviar a la **Papelera de reciclaje**.
  - Puedes añadir más carpetas.
- **Barra de título clara** en el tema claro, y opción **Abrir en pantalla completa** (apagada; **F11** en cualquier
  momento).
- La ventana se abre con un tamaño que cabe sobre la barra de tareas (pantallas al 125 %, portátiles).

## 1.5.0

- **Enlaces directos `.m3u8` / `.mpd`** (por ejemplo, los de Platzi cuando su extractor falla). Al pegar uno sale un
  panel propio, como el de torrents:
  - **Página de origen (Referer)**: se deduce del dominio (`mediastream.platzi.com` → `https://platzi.com/`) y la
    puedes cambiar.
  - **Nombre del archivo**: si ya existe, se añade `-2`, `-3`…
  - **Comprobación previa sin descargar**: dice si el enlace responde, con fragmentos, duración y calidad, o el
    motivo del fallo (403, 404, 410/token caducado, red). También avisa si está cifrado (AES-128 o DRM).
  - Si la comprobación falla, puedes **descargar de todos modos**.
  - Se descarga con la configuración predeterminada de yt-dlp, como
    `yt-dlp --referer REF -o "NOMBRE.%(ext)s" URL`.
  - Los **tokens** de la URL (`cP`, `pid`, `sid`, `token`, `signature`…) no se guardan en disco ni salen en el log.
- **Mostrar log completo (debug)**, en *Ajustes → Avanzado*:
  - ejecuta yt-dlp con `-v`;
  - en la Cola, **Ver detalle** muestra el error completo (por ejemplo `caused by SSLError('[SSL: UNEXPECTED_EOF_WHILE_READING]…')`)
    para buscarlo, y el log, con un botón **Copiar log**.
- **Plantillas de comando personalizado**, como en Seal: guarda varias, elige una, edítalas o bórralas.
- **Filtro del comando personalizado más estricto**:
  - solo se aceptan opciones de una lista de permitidas;
  - si se bloquea una, se dice cuál y por qué (`--exec`, `--use-postprocessor`, `--plugin-dirs`…);
  - una comilla sin cerrar indica dónde está.
- **Una sola instancia**: volver a abrir JabsDLP muestra la ventana que ya estaba abierta (antes se duplicaba al
  minimizarla a la bandeja). **Minimizar a la bandeja** viene ahora desactivado por defecto.
- **Actualizador de yt-dlp más seguro**:
  - valida el nombre y el origen (files.pythonhosted.org) de cada archivo;
  - vuelve a comprobar el SHA-256 antes de cargarlo;
  - una versión descargada con la 1.4.0 o anterior se vuelve a descargar una vez.

## 1.4.0

- **Una versión de yt-dlp que falla al cargar ya no se reintenta en bucle**: si la descargada no se puede importar,
  la app sigue usando la incluida y espera a que PyPI publique una más nueva antes de volver a descargarla.
  - Antes, cada búsqueda volvía a descargar la misma versión rota y borraba la marca de fallo.
- **El fallo de carga deja rastro**: el motivo del error y la versión que falló se guardan en el `estado.json` y se
  muestran en *Ajustes → Herramientas*; el traceback completo queda en
  `%LOCALAPPDATA%\JabsDLP\yt-dlp\error-carga.txt`.

## 1.3.0

- **Suplantar navegador (impersonation)**, nuevo ajuste en *Ajustes → Avanzado*: hace que las peticiones de
  yt-dlp parezcan venir de Chrome. Ayuda con sitios que bloquean la descarga con errores 403/410. Va
  **desactivado por defecto** y usa [curl_cffi](https://github.com/lexiforest/curl_cffi), incluido en el `.exe`.
  - Si el componente no está disponible, el switch aparece deshabilitado y se ve el motivo.
  - Si en el **comando personalizado** ya has escrito `--impersonate`, manda ese valor y el ajuste no lo pisa.
  - Con el motor **aria2**, la descarga en sí no usa impersonation (aria2 no lo soporta); solo el análisis y las peticiones de yt-dlp.

## 1.2.0

- **Idioma de la pista de audio**, ideal para los videos doblados de YouTube, e **idioma de los subtítulos**, manuales o automáticos.
- **Quitar anuncios** con [SponsorBlock](https://sponsor.ajay.app). Quita patrocinios, autopromoción, intros… Solo actúa si lo activas, y te enseña antes los tramos que va a quitar.
- **Recortar**: descarga solo el tramo que te interesa, por ejemplo de 1:20 a 3:45. El recorte se hace en tu equipo.
- **Reintentos automáticos** ante fallos de red o del servidor, configurables.
- **Retomar descargas** al volver a abrir la app, continuando los `.part`.
- **Límite de velocidad** total, repartido entre todas las descargas. Por defecto 5 MB/s; puedes ponerlo sin límite o personalizarlo.
- **Arrastrar y soltar** enlaces, o pulsar **Ctrl+V** en cualquier parte.
- **Notificaciones de Windows** al terminar, con botón para abrir la carpeta, e **icono en la bandeja** al minimizar.
- **Tema claro** e **inglés**.
- **Numerar** los archivos de una playlist (`01 - título.mp4`) y **no repetir descargas**.
- **aria2** como motor alternativo (opcional) y **torrents/magnet** sin seed.
- **Comando personalizado**: argumentos extra de yt-dlp.
