"""SponsorBlock: segmentos de patrocinio, autopromoción, etc. que los usuarios marcan en videos de YouTube.

Solo se consulta cuando el usuario activa "Quitar anuncios". Por privacidad se envía únicamente un prefijo de
4 caracteres del SHA-256 del ID del video (k-anonimato): el servidor devuelve los de muchos videos y aquí se
filtra el nuestro.
"""
import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request

API = 'https://sponsor.ajay.app'
CATEGORIAS = ('sponsor', 'selfpromo', 'interaction', 'intro', 'outro', 'preview', 'music_offtopic', 'filler')
SITIOS = ('Youtube',)


def categorias_validas(texto):
    return [c for c in (texto or '').split(',') if c in CATEGORIAS]


def segmentos(video_id, categorias, sitio='Youtube'):
    """Lista de {inicio, fin, categoria} ordenada, o [] si no hay. Lanza excepción si falla la red."""
    categorias = [c for c in categorias if c in CATEGORIAS]
    if not video_id or not categorias or sitio not in SITIOS:
        return []
    prefijo = hashlib.sha256(video_id.encode('utf-8')).hexdigest()[:4]
    consulta = urllib.parse.urlencode({'categories': json.dumps(categorias), 'actionTypes': json.dumps(['skip'])})
    peticion = urllib.request.Request(f'{API}/api/skipSegments/{prefijo}?{consulta}', headers={'User-Agent': 'JabsDLP'})
    try:
        with urllib.request.urlopen(peticion, timeout=15) as resp:
            datos = json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 404:  # ningún video con ese prefijo tiene segmentos
            return []
        raise
    resultado = []
    for video in datos if isinstance(datos, list) else []:
        if video.get('videoID') != video_id:
            continue
        for s in video.get('segments') or []:
            inicio, fin = (s.get('segment') or [0, 0])[:2]
            if s.get('category') in categorias and fin > inicio:
                resultado.append({'inicio': round(inicio, 2), 'fin': round(fin, 2), 'categoria': s['category']})
    return sorted(resultado, key=lambda s: s['inicio'])


def duracion_total(lista):
    """Segundos que se quitan, uniendo segmentos solapados."""
    total, fin_actual = 0.0, None
    for s in sorted(lista, key=lambda s: s['inicio']):
        inicio = s['inicio'] if fin_actual is None else max(s['inicio'], fin_actual)
        if s['fin'] > inicio:
            total += s['fin'] - inicio
            fin_actual = s['fin']
    return round(total, 1)
