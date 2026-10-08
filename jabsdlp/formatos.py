"""Elección de formatos: la opción recomendada (según el criterio Auto) y las listas manuales."""

FAMILIAS_VIDEO = (
    ('av1', ('av01', 'av1')),
    ('vp9', ('vp09', 'vp9')),
    ('h265', ('hvc1', 'hev1', 'hevc', 'h265')),
    ('h264', ('avc1', 'avc3', 'h264')),
    ('vp8', ('vp8',)),
)
PUNTAJE_VIDEO = {'av1': 4, 'vp9': 3, 'h265': 2, 'h264': 1, 'vp8': 0, 'otro': 0}
NOMBRE_VIDEO = {'av1': 'AV1', 'vp9': 'VP9', 'h265': 'H.265', 'h264': 'H.264', 'vp8': 'VP8', 'otro': 'Video'}

FAMILIAS_AUDIO = (
    ('opus', ('opus',)),
    ('aac', ('mp4a', 'aac')),
    ('mp3', ('mp3',)),
    ('vorbis', ('vorbis',)),
    ('flac', ('flac',)),
    ('eac3', ('ec-3', 'eac3')),
    ('ac3', ('ac-3', 'ac3')),
)
PUNTAJE_AUDIO = {'opus': 3, 'aac': 2, 'vorbis': 1, 'mp3': 1, 'flac': 1, 'eac3': 0, 'ac3': 0, 'otro': 0}
NOMBRE_AUDIO = {'opus': 'Opus', 'aac': 'AAC', 'mp3': 'MP3', 'vorbis': 'Vorbis', 'flac': 'FLAC',
                'eac3': 'E-AC3', 'ac3': 'AC3', 'otro': 'Audio'}
EXT_AUDIO = {'opus': 'opus', 'aac': 'm4a', 'mp3': 'mp3', 'vorbis': 'ogg', 'flac': 'flac'}
AUDIO_FORMATO_FAMILIA = {'m4a': 'aac', 'opus': 'opus', 'mp3': 'mp3', 'flac': 'flac'}

# Regex para filtrar por códec en los selectores de formato de yt-dlp (playlists y lotes)
FILTRO_CODEC = {
    'h264': "[vcodec~='^(avc1|avc3|h264)']",
    'h265': "[vcodec~='^(hvc1|hev1|hevc|h265)']",
    'av1': "[vcodec~='^(av01|av1)']",
    'vp9': "[vcodec~='^(vp09|vp9)']",
}
CODECS_RECODIFICABLES = ('h264', 'h265')
COMPATIBLES = {
    'mp4': ({'h264', 'h265', 'av1', 'vp9', None}, {'aac', 'opus', 'mp3', 'ac3', 'eac3', 'flac', None}),
    'webm': ({'vp9', 'vp8', 'av1', None}, {'opus', 'vorbis', None}),
}

CRITERIOS = ('equilibrado', 'ahorro', 'calidad')
NOMBRE_CRITERIO = {'equilibrado': 'Equilibrado', 'ahorro': 'Ahorro', 'calidad': 'Máxima calidad'}
TOPE_AHORRO = 720         # resolución máxima del criterio "ahorro" cuando la resolución está en Auto
UMBRAL_MEDIA = 100        # kbps: audio de calidad media
UMBRAL_BAJA = 64          # kbps: audio de calidad baja
NIVELES_AUDIO = ('alta', 'media', 'baja')


def _familia(codec, familias):
    codec = (codec or '').lower()
    if not codec or codec == 'none':
        return None
    for nombre, prefijos in familias:
        if codec.startswith(prefijos):
            return nombre
    return 'otro'


def familia_video(vcodec):
    return _familia(vcodec, FAMILIAS_VIDEO)


def familia_audio(acodec):
    return _familia(acodec, FAMILIAS_AUDIO)


def normalizar(prefs):
    """Rellena valores por defecto y convierte formatos antiguos (audio True/False)."""
    p = dict(prefs or {})
    audio = p.get('audio', 'auto')
    if audio is True or audio == 'true':
        audio = 'auto'
    elif audio is False or audio == 'false':
        audio = 'no'
    p['audio'] = audio if audio in ('auto', 'no', 'custom') else 'auto'
    if p.get('criterio') not in CRITERIOS:
        p['criterio'] = 'equilibrado'
    if p.get('audio_calidad') not in NIVELES_AUDIO:
        p['audio_calidad'] = 'alta'
    p.setdefault('tipo', 'video')
    p.setdefault('codec', 'auto')
    p.setdefault('resolucion', 'auto')
    p.setdefault('contenedor', 'auto')
    p.setdefault('formato_audio', 'auto')
    return p


def clase(f):
    """'video', 'audio', 'combinado' o None (storyboards, DRM...)."""
    if f.get('ext') == 'mhtml' or f.get('has_drm') or (f.get('format_note') or '').lower() == 'storyboard':
        return None
    vc, ac = f.get('vcodec'), f.get('acodec')
    hay_video = vc != 'none' and (vc is not None or bool(f.get('height')) or ac is None)
    hay_audio = ac != 'none' and (ac is not None or vc in (None, 'none'))
    if hay_video and hay_audio:
        return 'combinado'
    if hay_video:
        return 'video'
    if hay_audio:
        return 'audio'
    return None


def tamano(f, duracion=None):
    valor = f.get('filesize') or f.get('filesize_approx')
    if valor:
        return int(valor)
    if f.get('tbr') and duracion:
        return int(f['tbr'] * 125 * duracion)
    return None


def _suma(*valores):
    if any(v is None for v in valores):
        return None
    return sum(valores)


def es_drc(f):
    return 'drc' in (f.get('format_id') or '').lower() or 'drc' in (f.get('format_note') or '').lower()


def es_hdr(f):
    rango = (f.get('dynamic_range') or 'SDR').upper()
    return rango not in ('SDR', '')


def _preferencia_idioma(f):
    return f.get('language_preference') if f.get('language_preference') is not None else -1


def _abr(f):
    return f.get('abr') or f.get('tbr') or 0


def _clave_audio(f, preferir=None):
    fam = familia_audio(f.get('acodec'))
    return (
        _preferencia_idioma(f),
        not es_drc(f),
        fam == preferir,
        PUNTAJE_AUDIO.get(fam, 0),
        _abr(f),
        f.get('protocol', '').startswith('http') and 'm3u8' not in f.get('protocol', ''),
    )


def audio_por_nivel(formatos, nivel='alta', preferir=None):
    audios = [f for f in formatos if clase(f) == 'audio']
    if not audios:
        return None
    if nivel == 'alta':
        return max(audios, key=lambda f: _clave_audio(f, preferir))
    limpios = [f for f in audios if not es_drc(f)] or audios
    idioma = max(_preferencia_idioma(f) for f in limpios)
    limpios = [f for f in limpios if _preferencia_idioma(f) == idioma]
    tope = UMBRAL_MEDIA if nivel == 'media' else UMBRAL_BAJA
    debajo = [f for f in limpios if 0 < _abr(f) <= tope]
    if debajo:
        return max(debajo, key=lambda f: (familia_audio(f.get('acodec')) == preferir,
                                          PUNTAJE_AUDIO.get(familia_audio(f.get('acodec')), 0), _abr(f)))
    return min(limpios, key=_abr)


def mejor_audio(formatos, preferir=None):
    return audio_por_nivel(formatos, 'alta', preferir)


def elegir_audio(formatos, prefs, audio_id=None):
    """La pista de audio que acompaña al video según Con audio / Sin audio / Personalizado."""
    prefs = normalizar(prefs)
    if prefs['audio'] == 'no':
        return None
    if audio_id:
        for f in formatos:
            if f.get('format_id') == audio_id and clase(f) == 'audio':
                return f
    preferir = 'aac' if prefs['codec'] in CODECS_RECODIFICABLES else 'opus'
    if prefs['audio'] == 'custom':
        nivel = prefs['audio_calidad']
    else:
        nivel = 'media' if prefs['criterio'] == 'ahorro' else 'alta'
    return audio_por_nivel(formatos, nivel, preferir)


def contenedor_para(vfam, afam, preferido='auto', recodificar=None):
    """Contenedor final. Si el elegido no admite los códecs, se usa MKV."""
    if recodificar:
        vfam = recodificar
    if preferido in COMPATIBLES:
        videos, audios = COMPATIBLES[preferido]
        if vfam in videos and afam in audios:
            return preferido
        return 'mkv'
    if preferido == 'mkv':
        return 'mkv'
    videos, audios = COMPATIBLES['mp4']
    return 'mp4' if vfam in videos and afam in audios else 'mkv'


def _es_directo(f):
    protocolo = f.get('protocol') or ''
    return protocolo.startswith('http') and 'm3u8' not in protocolo


def _titulo_video(altura, vfam, afam):
    texto = ' · '.join([f'{altura}p' if altura else 'Original', NOMBRE_VIDEO.get(vfam or 'otro', 'Video')])
    if afam:
        texto += ' + ' + NOMBRE_AUDIO.get(afam, 'Audio')
    return texto


def _nombre_idioma(f):
    nota = (f.get('format_note') or '').lower()
    idioma = f.get('language')
    if idioma and ('original' in nota or 'default' in nota):
        return f'{idioma} (original)'
    return idioma


def opciones_video(info, prefs, audio_id=None):
    prefs = normalizar(prefs)
    duracion = info.get('duration')
    formatos = info.get('formats') or []
    codec_pref = prefs['codec']
    con_audio = prefs['audio'] != 'no'
    audio = elegir_audio(formatos, prefs, audio_id)

    videos = [f for f in formatos if clase(f) in ('video', 'combinado')]
    if (not con_audio or audio is not None) and any(clase(f) == 'video' for f in videos):
        # Sin audio, o con una pista aparte: solo videos sin audio (evita dos pistas de audio)
        videos = [f for f in videos if clase(f) == 'video']

    # Quitar duplicados (misma altura/códec/fps/HDR por https y por m3u8): se queda el directo y más pequeño
    unicos = {}
    for f in videos:
        clave = (f.get('height'), familia_video(f.get('vcodec')), round(f.get('fps') or 0), es_hdr(f), clase(f))
        actual = unicos.get(clave)
        candidato = (not _es_directo(f), tamano(f, duracion) or float('inf'))
        if actual is None or candidato < (not _es_directo(actual), tamano(actual, duracion) or float('inf')):
            unicos[clave] = f

    opciones = []
    for f in unicos.values():
        vfam = familia_video(f.get('vcodec'))
        if clase(f) == 'combinado':
            spec, afam, peso, abr = f['format_id'], familia_audio(f.get('acodec')) or 'otro', tamano(f, duracion), 0
            ids = f['format_id']
        elif audio is not None:
            spec = f"{f['format_id']}+{audio['format_id']}"
            afam = familia_audio(audio.get('acodec')) or 'otro'
            peso = _suma(tamano(f, duracion), tamano(audio, duracion))
            abr = _abr(audio)
            ids = f"{f['format_id']} + {audio['format_id']}"
        else:
            spec, afam, peso, abr, ids = f['format_id'], None, tamano(f, duracion), 0, f['format_id']
        recodificar = codec_pref if codec_pref in CODECS_RECODIFICABLES and vfam != codec_pref else None
        tbr = (f.get('tbr') or f.get('vbr') or 0) + abr
        opciones.append({
            'spec': spec,
            'titulo': _titulo_video(f.get('height'), vfam, afam),
            'altura': f.get('height'),
            'ancho': f.get('width'),
            'fps': f.get('fps'),
            'hdr': es_hdr(f),
            'vcodec': vfam,
            'acodec': afam,
            'puntaje': PUNTAJE_VIDEO.get(vfam or 'otro', 0),
            'tamano': peso,
            'tbr': round(tbr, 1) if tbr else None,
            'contenedor': contenedor_para(vfam, afam, prefs['contenedor'], recodificar),
            'video': True,
            'audio': afam is not None,
            'recodificar': recodificar,
            'ids': ids,
        })
    opciones.sort(key=lambda o: (-(o['altura'] or 0), -(o['fps'] or 0), o['hdr'], -o['puntaje'], _peso(o)))
    return opciones


def _peso(o):
    return o['tamano'] if o['tamano'] is not None else float('inf')


def recomendar_video(opciones, prefs):
    if not opciones:
        return None
    prefs = normalizar(prefs)
    criterio = prefs['criterio']
    alturas = sorted({o['altura'] or 0 for o in opciones})
    resolucion = prefs['resolucion']
    if str(resolucion).isdigit():
        objetivo = int(resolucion)
    else:
        objetivo = min(alturas[-1], TOPE_AHORRO) if criterio == 'ahorro' else alturas[-1]
    validas = [a for a in alturas if a <= objetivo]
    altura = validas[-1] if validas else alturas[0]

    base = [o for o in opciones if (o['altura'] or 0) == altura]
    if any(not o['hdr'] for o in base):
        base = [o for o in base if not o['hdr']]
    elegir_fps = min if criterio == 'ahorro' else max
    fps_objetivo = elegir_fps((o['fps'] or 0) for o in base)
    base = [o for o in base if (o['fps'] or 0) == fps_objetivo]

    candidatas = base
    aviso = None
    codec_pref = prefs['codec']
    if codec_pref != 'auto':
        exactas = [o for o in base if o['vcodec'] == codec_pref]
        if exactas:
            candidatas = exactas
        elif codec_pref not in CODECS_RECODIFICABLES:
            aviso = f'{NOMBRE_VIDEO[codec_pref]} no está disponible en {altura}p; se usa el mejor códec disponible.'

    if criterio == 'calidad':
        def clave(o):
            return -(o['tbr'] or 0), -o['puntaje']
    elif criterio == 'ahorro':
        def clave(o):
            return _peso(o), -o['puntaje']
    else:
        def clave(o):
            return -o['puntaje'], _peso(o)
    elegida = dict(min(candidatas, key=clave))

    etiquetas = [NOMBRE_CRITERIO[criterio]]
    if elegida['puntaje'] == max(o['puntaje'] for o in base):
        etiquetas.append('Mejor códec')
    conocidos = [_peso(o) for o in base if o['tamano'] is not None]
    if conocidos and elegida['tamano'] is not None and elegida['tamano'] <= min(conocidos):
        etiquetas.append('Menor tamaño')
    if criterio == 'calidad' and (elegida['tbr'] or 0) >= max((o['tbr'] or 0) for o in base):
        etiquetas.append('Mayor bitrate')
    elegida['etiquetas'] = etiquetas
    elegida['aviso'] = aviso
    return elegida


def opciones_audio(info, prefs):
    prefs = normalizar(prefs)
    duracion = info.get('duration')
    formatos = info.get('formats') or []
    audios = [f for f in formatos if clase(f) == 'audio']
    if any(f.get('acodec') and _abr(f) for f in audios):
        audios = [f for f in audios if f.get('acodec') and _abr(f)]  # fuera pistas sin códec ni bitrate (HLS)
    fuente = audios or [f for f in formatos if clase(f) == 'combinado']
    formato_audio = prefs['formato_audio']

    unicos = {}
    for f in fuente:
        clave = (familia_audio(f.get('acodec')), round(_abr(f) / 16), f.get('language'), es_drc(f))
        actual = unicos.get(clave)
        if actual is None or _clave_audio(f) > _clave_audio(actual):
            unicos[clave] = f
    if any(not es_drc(f) for f in unicos.values()):
        unicos = {k: f for k, f in unicos.items() if not es_drc(f)}

    opciones = []
    for f in unicos.values():
        afam = familia_audio(f.get('acodec')) or 'otro'
        if formato_audio == 'auto':
            salida, recodificar = EXT_AUDIO.get(afam, 'm4a'), None
        else:
            salida = formato_audio
            recodificar = None if AUDIO_FORMATO_FAMILIA.get(formato_audio) == afam else formato_audio
        abr = _abr(f)
        opciones.append({
            'spec': f['format_id'],
            'titulo': NOMBRE_AUDIO.get(afam, 'Audio') + (f' · {round(abr)} kbps' if abr else ''),
            'idioma': _nombre_idioma(f),
            'acodec': afam,
            'abr': abr,
            'tamano': tamano(f, duracion),
            'contenedor': salida,
            'video': False,
            'audio': True,
            'recodificar': recodificar,
            'ids': f['format_id'],
            '_clave': _clave_audio(f, AUDIO_FORMATO_FAMILIA.get(formato_audio)),
        })
    opciones.sort(key=lambda o: o['_clave'], reverse=True)
    return opciones


def recomendar_audio(opciones, info, prefs):
    if not opciones:
        return None
    prefs = normalizar(prefs)
    criterio = prefs['criterio']
    if criterio == 'calidad':
        elegida = max(opciones, key=lambda o: (o['_clave'][0], o['abr'] or 0))
    elif criterio == 'ahorro':
        media = audio_por_nivel(info.get('formats') or [], 'media', AUDIO_FORMATO_FAMILIA.get(prefs['formato_audio']))
        elegida = next((o for o in opciones if media and o['spec'] == media['format_id']), opciones[-1])
    else:
        elegida = opciones[0]
    elegida = dict(elegida)
    etiquetas = [NOMBRE_CRITERIO[criterio]]
    if elegida.get('idioma') and 'original' in elegida['idioma']:
        etiquetas.append('Idioma original')
    if not elegida['recodificar']:
        etiquetas.append('Sin recodificar')
    elegida['etiquetas'] = etiquetas
    elegida['aviso'] = None
    return elegida


def calcular(info, prefs, audio_id=None):
    """Recomendado + lista manual (+ pistas de audio en modo video) para un video ya analizado."""
    prefs = normalizar(prefs)
    if prefs['tipo'] == 'audio':
        opciones = opciones_audio(info, prefs)
        recomendado = recomendar_audio(opciones, info, prefs)
        pistas, elegido = [], None
    else:
        opciones = opciones_video(info, prefs, audio_id)
        recomendado = recomendar_video(opciones, prefs)
        pistas = opciones_audio(info, dict(prefs, formato_audio='auto')) if prefs['audio'] != 'no' else []
        audio = elegir_audio(info.get('formats') or [], prefs, audio_id)
        elegido = audio['format_id'] if audio else None
    for o in opciones + pistas + ([recomendado] if recomendado else []):
        o.pop('_clave', None)
    return {'recomendado': recomendado, 'opciones': opciones, 'audios': pistas, 'audio_elegido': elegido}


def _unir(*partes):
    vistas = []
    for p in partes:
        if p not in vistas:
            vistas.append(p)
    return '/'.join(vistas)


SIN_DRC = '[format_id!*=drc]'  # las pistas DRC (volumen comprimido) solo como último recurso


def _audios_selector(filtro='', tope=''):
    return [f'ba{SIN_DRC}{filtro}{tope}', f'ba{SIN_DRC}{tope}', f'ba{filtro}{tope}', f'ba{tope}', f'ba{SIN_DRC}', 'ba']


def selector_por_preferencias(prefs):
    """format + format_sort para playlists y lotes, donde no se analiza cada video antes."""
    prefs = normalizar(prefs)
    criterio = prefs['criterio']
    if prefs['tipo'] == 'audio':
        familia = AUDIO_FORMATO_FAMILIA.get(prefs['formato_audio'])
        filtro = {'aac': '[acodec^=mp4a]', 'opus': '[acodec=opus]', 'mp3': '[acodec=mp3]'}.get(familia, '')
        tope = f'[abr<=?{UMBRAL_MEDIA}]' if criterio == 'ahorro' else ''
        orden = ['lang', 'abr', 'acodec'] if criterio == 'calidad' else ['lang', 'acodec', 'abr']
        return _unir(*_audios_selector(filtro, tope), 'b'), orden

    codec = prefs['codec']
    filtro = FILTRO_CODEC.get(codec, '')
    if prefs['audio'] == 'no':
        formato = _unir(f'bv{filtro}', 'bv', 'bv*')
    else:
        nivel = prefs['audio_calidad'] if prefs['audio'] == 'custom' else ('media' if criterio == 'ahorro' else 'alta')
        tope = {'media': f'[abr<=?{UMBRAL_MEDIA}]', 'baja': f'[abr<=?{UMBRAL_BAJA}]'}.get(nivel, '')
        filtro_audio = '[acodec^=mp4a]' if codec in CODECS_RECODIFICABLES else ''
        formato = _unir(*(f'bv{filtro}+{a}' for a in _audios_selector(filtro_audio, tope)),
                        f'bv+ba{SIN_DRC}', 'bv+ba', f'b{filtro}', 'b')
    resolucion = prefs['resolucion']
    if str(resolucion).isdigit():
        res = f'res:{resolucion}'
    else:
        res = f'res:{TOPE_AHORRO}' if criterio == 'ahorro' else 'res'
    if criterio == 'calidad':
        orden = ['lang', res, 'fps', 'hdr:sdr', 'tbr', 'vcodec', 'acodec']
    elif criterio == 'ahorro':
        orden = ['lang', res, '+fps', 'hdr:sdr', 'acodec', 'abr', '+size', 'vcodec']
    else:
        orden = ['lang', res, 'fps', 'hdr:sdr', 'vcodec', 'acodec', 'abr', '+size']
    return formato, orden


def necesita_recodificar(vcodec, prefs):
    prefs = normalizar(prefs)
    objetivo = prefs['codec']
    if prefs['tipo'] == 'audio' or objetivo not in CODECS_RECODIFICABLES:
        return None
    return objetivo if familia_video(vcodec) != objetivo else None
