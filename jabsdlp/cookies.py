import glob
import os
import tempfile

PREFIJO_TEMPORAL = 'jabsdlp_cookies_'


def normalize_netscape_cookie_file(cookies_path):
    normalized = tempfile.NamedTemporaryFile(delete=False, prefix=PREFIJO_TEMPORAL, suffix='.txt', mode='w', encoding='utf-8')
    wrote_header = False
    with open(cookies_path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            raw_line = line.rstrip('\r\n')
            if not raw_line:
                continue
            if raw_line.startswith('#'):
                if raw_line.startswith('# Netscape HTTP Cookie File'):
                    normalized.write(raw_line + '\n')
                    wrote_header = True
                continue
            parts = raw_line.split('\t')
            if len(parts) != 7:
                continue
            domain, include_subdomains, path, secure, expiration, name, value = parts
            if domain.startswith('.') and include_subdomains.upper() == 'FALSE':
                include_subdomains = 'TRUE'
            elif not domain.startswith('.') and include_subdomains.upper() == 'TRUE':
                domain = '.' + domain
            normalized.write('\t'.join([domain, include_subdomains, path, secure, expiration, name, value]) + '\n')
    normalized.close()
    if not wrote_header:
        with open(normalized.name, 'r+', encoding='utf-8') as nf:
            contents = nf.read()
            nf.seek(0)
            nf.write('# Netscape HTTP Cookie File\n' + contents)
    return normalized.name


NAVEGADORES = ('firefox', 'chrome', 'edge', 'brave', 'opera', 'vivaldi', 'chromium')


def opciones_cookies(ajustes):
    """Devuelve (opciones_ytdlp, archivo_temporal). El temporal se borra con borrar_temporal()."""
    modo = ajustes.get('cookies_modo')
    if modo == 'archivo':
        ruta = ajustes.get('cookies_archivo')
        if not ruta or not os.path.isfile(ruta):
            raise FileNotFoundError('No se encuentra el archivo de cookies configurado en Ajustes.')
        temporal = normalize_netscape_cookie_file(ruta)
        return {'cookiefile': temporal}, temporal
    if modo == 'navegador':
        navegador = ajustes.get('cookies_navegador')
        if navegador in NAVEGADORES:
            return {'cookiesfrombrowser': (navegador, None, None, None)}, None
    return {}, None


def borrar_temporal(ruta):
    if ruta and os.path.exists(ruta):
        try:
            os.unlink(ruta)
        except OSError:
            pass


def limpiar_temporales_huerfanos():
    """Borra copias de cookies que hubieran quedado en %TEMP% si la app se cerró de golpe."""
    for ruta in glob.glob(os.path.join(tempfile.gettempdir(), PREFIJO_TEMPORAL + '*.txt')):
        borrar_temporal(ruta)
