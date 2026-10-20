"""Comando personalizado: argumentos extra de yt-dlp escritos como en la consola (Ajustes → Avanzado).

Dos capas de filtro:
1. Cada opción se resuelve con el parser oficial de yt-dlp (alias cortos, abreviaturas y "--opcion=valor") y se
   comprueba contra una lista de bloqueo con el motivo (ejecutar programas, cargar código o archivos externos,
   sacar las descargas de la carpeta elegida) y después contra una lista de opciones permitidas.
2. Sobre el resultado del parser se vuelven a comprobar las claves y los postprocesadores peligrosos.
Un ajuste manipulado nunca debe poder lanzar comandos.
"""
import shlex

EJECUTA = 'ejecuta programas del sistema'
CODIGO = 'carga código o configuración externa'
APP = 'la app ya lo gestiona'
BLOQUEADAS = {
    '--exec': EJECUTA, '--exec-before-download': EJECUTA, '--no-exec': EJECUTA, '--netrc-cmd': EJECUTA,
    '--use-postprocessor': 'carga postprocesadores (pueden ejecutar código)',
    '--postprocessor-args': 'pasa argumentos arbitrarios a ffmpeg (puede leer o escribir fuera de la carpeta)',
    '--downloader': 'usa un programa externo para descargar', '--external-downloader': 'usa un programa externo para descargar',
    '--downloader-args': 'pasa argumentos a un programa externo', '--external-downloader-args': 'pasa argumentos a un programa externo',
    '--plugin-dirs': CODIGO, '--no-plugin-dirs': CODIGO, '--config-locations': CODIGO, '--config-location': CODIGO,
    '--ignore-config': CODIGO, '--batch-file': 'lee URLs de un archivo', '--load-info-json': 'lee un archivo externo',
    '--ffmpeg-location': 'cambia el ffmpeg que se ejecuta', '--output': f'cambia dónde se guarda ({APP})',
    '--paths': f'cambia dónde se guarda ({APP})', '--update': APP, '--update-to': APP, '--no-update': APP,
    '--cookies': f'lee cookies de un archivo ({APP}, en Ajustes → Cookies)',
    '--cookies-from-browser': f'lee las cookies del navegador ({APP}, en Ajustes → Cookies)',
    '--print-to-file': 'escribe archivos fuera de la carpeta', '--write-link': 'crea accesos directos',
    '--username': 'no guardes contraseñas aquí', '--password': 'no guardes contraseñas aquí',
    '--video-password': 'no guardes contraseñas aquí', '--ap-password': 'no guardes contraseñas aquí',
    '--client-certificate-password': 'no guardes contraseñas aquí',
}
PERMITIDAS = {
    # red
    '--referer', '--add-headers', '--user-agent', '--impersonate', '--socket-timeout', '--source-address',
    '--force-ipv4', '--force-ipv6', '--proxy', '--geo-verification-proxy', '--xff', '--geo-bypass',
    '--no-geo-bypass', '--geo-bypass-country', '--no-check-certificates', '--prefer-insecure',
    '--legacy-server-connect', '--enable-file-urls', '--sleep-requests', '--sleep-interval', '--max-sleep-interval',
    '--sleep-subtitles', '--limit-rate', '--throttled-rate', '--retries', '--fragment-retries',
    '--file-access-retries', '--retry-sleep', '--extractor-retries', '--skip-unavailable-fragments',
    '--abort-on-unavailable-fragments', '--concurrent-fragments', '--buffer-size', '--http-chunk-size',
    '--hls-use-mpegts', '--no-hls-use-mpegts', '--download-sections', '--live-from-start', '--no-live-from-start',
    '--wait-for-video', '--no-wait-for-video',
    # formato
    '--format', '--format-sort', '--format-sort-force', '--no-format-sort-force', '--merge-output-format',
    '--video-multistreams', '--no-video-multistreams', '--audio-multistreams', '--no-audio-multistreams',
    '--prefer-free-formats', '--no-prefer-free-formats', '--check-formats', '--check-all-formats',
    '--no-check-formats', '--extract-audio', '--audio-format', '--audio-quality', '--remux-video', '--recode-video',
    '--keep-video', '--no-keep-video', '--fixup',
    # subtítulos, miniaturas y metadatos
    '--sub-langs', '--sub-format', '--convert-subs', '--convert-thumbnails', '--add-metadata', '--no-add-metadata',
    '--parse-metadata', '--replace-in-metadata', '--xattrs', '--concat-playlist', '--split-chapters',
    '--no-split-chapters', '--remove-chapters', '--no-remove-chapters', '--force-keyframes-at-cuts',
    '--no-force-keyframes-at-cuts',
    # selección y archivos
    '--playlist-items', '--match-filters', '--no-match-filters', '--break-match-filters', '--date', '--datebefore',
    '--dateafter', '--age-limit', '--min-filesize', '--max-filesize', '--ignore-errors', '--no-abort-on-error',
    '--abort-on-error', '--yes-playlist', '--no-playlist', '--mark-watched', '--no-mark-watched',
    '--restrict-filenames', '--no-restrict-filenames', '--windows-filenames', '--no-windows-filenames',
    '--trim-filenames', '--no-overwrites', '--force-overwrites', '--no-force-overwrites', '--continue',
    '--no-continue', '--part', '--no-part', '--mtime', '--no-mtime', '--extractor-args', '--compat-options',
    '--verbose', '--no-warnings', '--ignore-no-formats-error', '--no-ignore-no-formats-error',
}
# Familias enteras inofensivas (--embed-subs, --no-embed-chapters, --write-subs, --sponsorblock-remove…)
PREFIJOS_PERMITIDOS = ('--embed-', '--no-embed-', '--write-', '--no-write-', '--sponsorblock-', '--no-sponsorblock')
CLAVES_BLOQUEADAS = {'netrc_cmd', 'external_downloader', 'external_downloader_args', 'ffmpeg_location', 'paths',
                     'outtmpl', 'plugin_dirs', 'cookiefile', 'cookiesfrombrowser', 'print_to_file', 'logger',
                     'progress_hooks', 'postprocessor_hooks', 'post_hooks', 'postprocessor_args', 'username',
                     'password', 'videopassword', 'ap_password', 'client_certificate_password', 'writelink',
                     'writeurllink', 'writewebloclink', 'writedesktoplink'}
POSTPROCESADORES_BLOQUEADOS = {'Exec'}


class ArgumentosInvalidos(ValueError):
    pass


def _parser():
    from yt_dlp.options import create_parser
    return create_parser()


def _dividir(texto):
    """shlex.split, pero si falta cerrar una comilla dice dónde: 'Comilla " sin cerrar en: "https://…'."""
    try:
        return shlex.split(texto, posix=True)
    except ValueError:
        abierta, inicio, i = None, 0, 0
        while i < len(texto):
            c = texto[i]
            if abierta:
                if c == '\\' and abierta == '"' and i + 1 < len(texto):
                    i += 1
                elif c == abierta:
                    abierta = None
            elif c == '\\' and i + 1 < len(texto):
                i += 1
            elif c in '"\'':
                abierta, inicio = c, i
            i += 1
        trozo = texto[inicio:inicio + 60] + ('…' if len(texto) - inicio > 60 else '')
        raise ArgumentosInvalidos(f'Comilla {abierta or ""} sin cerrar en: {trozo}') from None


def _opcion(parser, arg):
    """(Option de optparse, ¿el valor va pegado?) para un argumento que empieza por '-'."""
    import optparse
    if arg.startswith('--'):
        nombre, igual, _ = arg.partition('=')
        try:
            nombre = parser._match_long_opt(nombre)   # resuelve abreviaturas como hace yt-dlp
        except (optparse.BadOptionError, optparse.AmbiguousOptionError) as e:
            raise ArgumentosInvalidos(f'{arg.split("=", 1)[0]}: {"opción ambigua" if "ambiguous" in str(e) else "opción desconocida"}.') from None
        return parser._long_opt[nombre], bool(igual)
    opcion = parser._short_opt.get(arg[:2])
    if opcion is None:
        raise ArgumentosInvalidos(f'{arg[:2]}: opción desconocida.')
    return opcion, len(arg) > 2


def _revisar(lista):
    """Recorre las opciones: bloqueadas (con motivo), no permitidas y URLs sueltas."""
    parser = _parser()
    i = 0
    while i < len(lista):
        arg = lista[i]
        if not arg.startswith('-') or arg == '-':
            if arg.lower().startswith(('http://', 'https://')):
                raise ArgumentosInvalidos('No pongas URLs aquí: solo argumentos.')
            raise ArgumentosInvalidos(f'"{arg[:60]}" sobra o le falta la opción a la que acompaña.')
        opcion, pegado = _opcion(parser, arg)
        nombres = list(opcion._long_opts) + list(opcion._short_opts)
        visible = next((n for n in nombres if n == arg.split('=', 1)[0]), opcion.get_opt_string())
        motivo = next((BLOQUEADAS[n] for n in nombres if n in BLOQUEADAS), None)
        if motivo:
            raise ArgumentosInvalidos(f'Se bloqueó {visible}: {motivo}.')
        if not any(n in PERMITIDAS or n.startswith(PREFIJOS_PERMITIDOS) for n in opcion._long_opts):
            raise ArgumentosInvalidos(f'{visible} no está en la lista de opciones permitidas.')
        if opcion.takes_value() and not pegado:
            if i + opcion.nargs >= len(lista):
                raise ArgumentosInvalidos(f'A {visible} le falta su valor.')
            i += opcion.nargs
        i += 1


def _parsear(lista):
    import yt_dlp
    try:
        return yt_dlp.parse_options(['--ignore-config', *lista]).ydl_opts
    except (SystemExit, Exception) as e:  # noqa: BLE001 - optparse informa los errores de sintaxis así
        lineas = [l.strip() for l in str(e).splitlines() if l.strip()]
        detalle = lineas[-1].split('error:', 1)[-1].strip() if lineas else 'sintaxis incorrecta'
        raise ArgumentosInvalidos(f'Argumentos no válidos: {detalle}') from None


def interpretar(texto):
    """Devuelve (opciones_extra, postprocesadores_extra). Lanza ArgumentosInvalidos si algo no se permite."""
    texto = (texto or '').strip()
    if not texto:
        return {}, []
    lista = _dividir(texto)
    _revisar(lista)
    base = _parsear([])
    elegidas = _parsear(lista)
    extra = {k: v for k, v in elegidas.items() if k != 'postprocessors' and base.get(k) != v}
    bloqueadas = sorted(k for k in extra if k in CLAVES_BLOQUEADAS)
    if bloqueadas:
        raise ArgumentosInvalidos('No se permiten estas opciones: ' + ', '.join(bloqueadas))
    pps = [p for p in elegidas.get('postprocessors') or [] if p not in (base.get('postprocessors') or [])]
    if any(p.get('key') in POSTPROCESADORES_BLOQUEADOS for p in pps):
        raise ArgumentosInvalidos('No se permiten postprocesadores que ejecutan programas.')
    return extra, pps
