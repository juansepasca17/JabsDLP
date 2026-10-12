"""Comando personalizado: argumentos extra de yt-dlp escritos como en la consola (Ajustes → Avanzado).

Se interpretan con el parser oficial de yt-dlp y solo se aplican las opciones que cambian respecto a los valores
por defecto. Se bloquean las que ejecutan programas, cargan código o archivos externos, o mueven las descargas
fuera de la carpeta elegida: un ajuste manipulado nunca debe poder lanzar comandos.
"""
import shlex

BLOQUEADOS = {
    '--exec', '--exec-before-download', '--no-exec', '--netrc-cmd', '--plugin-dirs', '--config-location',
    '--config-locations', '--batch-file', '-a', '--load-info-json', '--downloader', '--external-downloader',
    '--downloader-args', '--external-downloader-args', '--ffmpeg-location', '-P', '--paths', '-o', '--output',
    '--update', '-U', '--update-to', '--cookies-from-browser', '--cookies', '--print-to-file', '--write-link',
    '--use-postprocessor',
}
CLAVES_BLOQUEADAS = {'netrc_cmd', 'external_downloader', 'external_downloader_args', 'ffmpeg_location', 'paths',
                     'outtmpl', 'plugin_dirs', 'cookiefile', 'cookiesfrombrowser', 'print_to_file', 'logger',
                     'progress_hooks', 'postprocessor_hooks', 'post_hooks'}
POSTPROCESADORES_BLOQUEADOS = {'Exec'}


class ArgumentosInvalidos(ValueError):
    pass


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
    try:
        lista = shlex.split(texto, posix=True)
    except ValueError as e:
        raise ArgumentosInvalidos(f'Comillas sin cerrar: {e}') from None
    prohibidos = sorted({a.split('=', 1)[0] for a in lista if a.split('=', 1)[0] in BLOQUEADOS})
    if prohibidos:
        raise ArgumentosInvalidos('No se permiten por seguridad o porque la app ya los gestiona: ' + ', '.join(prohibidos))
    urls = [a for a in lista if a.lower().startswith(('http://', 'https://'))]
    if urls:
        raise ArgumentosInvalidos('No pongas URLs aquí: solo argumentos.')
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
