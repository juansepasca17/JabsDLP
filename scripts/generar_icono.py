"""Genera el logo de JabsDLP: un guante de boxeo lanzando un jab, con líneas de velocidad.

Crea assets/icono.ico (ventana y .exe), assets/icono.png y ui/logo.png. Solo se usa al compilar.
"""
import os

from PIL import Image, ImageChops, ImageDraw

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COLORES = ((248, 82, 82), (220, 38, 38), (153, 27, 27))  # rojo claro, rojo, rojo oscuro


def degradado(tam):
    img = Image.new('RGB', (tam, tam))
    px = img.load()
    a, b, c = COLORES
    for y in range(tam):
        for x in range(tam):
            t = (x + y) / (2 * (tam - 1))
            if t < 0.5:
                k, i, f = t / 0.5, a, b
            else:
                k, i, f = (t - 0.5) / 0.5, b, c
            px[x, y] = tuple(round(i[n] + (f[n] - i[n]) * k) for n in range(3))
    return img


def bezier(p0, p1, p2, pasos=40):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1])
            for t in (i / pasos for i in range(pasos + 1))]


def linea_redonda(d, puntos, ancho, color):
    d.line(puntos, fill=color, width=ancho, joint='curve')
    for x, y in (puntos[0], puntos[-1]):
        d.ellipse((x - ancho / 2, y - ancho / 2, x + ancho / 2, y + ancho / 2), fill=color)


def guante_vertical(t=512):
    """Guante de boxeo de pie (puño arriba, muñeca abajo) dibujado a 512 px."""
    m = Image.new('L', (t, t), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle((168, 52, 392, 336), radius=112, fill=255)          # puño
    d.rectangle((182, 250, 378, 352), fill=255)                             # dorso hacia la muñeca
    d.ellipse((96, 176, 214, 344), fill=255, outline=0, width=16)           # pulgar (su borde marca la costura)
    d.rounded_rectangle((196, 368, 364, 462), radius=20, fill=255)           # muñequera
    linea_redonda(d, bezier((236, 112), (300, 92), (346, 140)), 14, 0)      # brillo de los nudillos
    return m


def guante(tam):
    """Máscara (L): guante apuntando a la derecha (jab) + líneas de velocidad."""
    base = guante_vertical().rotate(-90, resample=Image.BICUBIC)
    base = base.resize((380, 380), Image.LANCZOS)
    m = Image.new('L', (512, 512), 0)
    m.paste(base, (124, 66))
    d = ImageDraw.Draw(m)
    for y, x0 in ((198, 78), (258, 44), (318, 78)):
        linea_redonda(d, [(x0, y), (150, y)], 30, 255)
    return m.resize((tam, tam), Image.LANCZOS)


def icono(tam=512):
    fondo = degradado(tam).convert('RGBA')
    forma = Image.new('L', (tam, tam), 0)
    ImageDraw.Draw(forma).rounded_rectangle((0, 0, tam - 1, tam - 1), radius=int(tam * 0.24), fill=255)
    img = Image.new('RGBA', (tam, tam), (0, 0, 0, 0))
    img.paste(fondo, (0, 0), forma)
    blanco = Image.new('RGBA', (tam, tam), (255, 255, 255, 255))
    img.paste(blanco, (0, 0), ImageChops.multiply(guante(tam), forma))
    return img


if __name__ == '__main__':
    grande = icono(1024).resize((512, 512), Image.LANCZOS)  # dibujado al doble para bordes suaves
    os.makedirs(os.path.join(RAIZ, 'assets'), exist_ok=True)
    grande.save(os.path.join(RAIZ, 'assets', 'icono.ico'),
                sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    grande.resize((256, 256), Image.LANCZOS).save(os.path.join(RAIZ, 'assets', 'icono.png'))
    grande.resize((96, 96), Image.LANCZOS).save(os.path.join(RAIZ, 'ui', 'logo.png'))
    print('Logo generado en assets/ y ui/logo.png')
