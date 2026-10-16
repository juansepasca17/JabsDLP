"""Impersonation: suplantar la huella TLS/HTTP de un navegador (Chrome) en las peticiones de yt-dlp.

Útil con sitios que responden 403/410 a clientes con la huella de Python. Lo hace curl_cffi, una
dependencia aparte de yt-dlp: en la app va incluida en el .exe y en desarrollo en el .venv, y el
actualizador de yt-dlp no la toca (solo intercepta yt_dlp y yt_dlp_ejs al importar).

La versión de yt-dlp puede ser la incluida o una descargada por el actualizador, así que todo se
comprueba con la versión EN USO: se usa el mismo criterio que usa yt-dlp para decidir si lanza
"Impersonate target ... is not available" al crear YoutubeDL, sin asumir APIs públicas nuevas.
"""
MOTIVO_SIN_CURL = 'Falta el componente curl_cffi.'
MOTIVO_SIN_OBJETIVO = 'La versión de yt-dlp en uso no admite suplantar a Chrome.'

_cache = None


def objetivo_chrome():
    from yt_dlp.networking.impersonate import ImpersonateTarget
    return ImpersonateTarget('chrome')


def _objetivo_disponible(ydl, objetivo):
    """¿Admite la versión de yt-dlp en uso ese objetivo? (mismo criterio que YoutubeDL.__init__)."""
    comprobar = getattr(ydl, '_impersonate_target_available', None)
    if comprobar is not None:
        return bool(comprobar(objetivo))
    # Versión de yt-dlp sin ese método: se recorren los handlers como hace --list-impersonate-targets
    return any(getattr(rh, 'is_supported_target', lambda _t: False)(objetivo)
               for rh in ydl._request_director.handlers.values())


def impersonation_disponible(forzar=False):
    """(disponible, motivo). El motivo es None si está disponible; nunca lanza."""
    global _cache
    if _cache is not None and not forzar:
        return _cache
    try:
        import curl_cffi  # noqa: F401 - solo comprueba que se puede importar
    except Exception:  # noqa: BLE001
        _cache = (False, MOTIVO_SIN_CURL)
        return _cache
    try:
        import yt_dlp
        objetivo = objetivo_chrome()
        with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
            disponible = _objetivo_disponible(ydl, objetivo)
    except Exception as e:  # noqa: BLE001 - ninguna comprobación debe tumbar la app
        _cache = (False, f'No se pudo comprobar la disponibilidad de impersonation: {type(e).__name__}.')
        return _cache
    _cache = (True, None) if disponible else (False, MOTIVO_SIN_OBJETIVO)
    return _cache


def aplicar_impersonacion(opciones, ajustes):
    """Aplica el ajuste "impersonar" a un dict de opciones de yt-dlp.

    Si el dict ya trae "impersonate" (del comando personalizado), manda ese: con soporte se conserva
    y sin soporte se quita para que la descarga no falle al crear YoutubeDL. Devuelve un mensaje para
    el usuario si se ignoró algo, o None cuando no hay nada que avisar.
    """
    disponible, motivo = impersonation_disponible()
    if 'impersonate' in opciones and not disponible:
        del opciones['impersonate']
        return f'No se pudo aplicar --impersonate del comando personalizado: {motivo}'
    if ajustes.get('impersonar') and 'impersonate' not in opciones:
        if not disponible:
            return f'No se pudo activar la suplantación de navegador: {motivo}'
        opciones['impersonate'] = objetivo_chrome()
    return None
