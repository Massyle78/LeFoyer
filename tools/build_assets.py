"""Prépare les icônes et photos de la charte graphique.

Les icônes sont transformées en MASQUES transparents (noir + alpha) : le CSS les colore
(`mask-image`), donc on change la couleur d'une icône sans toucher au fichier.
Sources : dossier « new graphic chart » (captures de la charte) et pictos de la première version.

    python tools/build_assets.py

Les images sont des placeholders (générées par IA ou captures de maquette) : à remplacer et valider
avec Le Foyer. Pour remplacer une icône, déposer un PNG du même nom dans static/img/icons.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parent.parent
CHART = ROOT.parent / "new graphic chart"
OLD = ROOT.parent / "bus_buddy" / "assets"
ICONS = ROOT / "static" / "img" / "icons"
STOPS = ROOT / "static" / "img" / "stops"
SCALE = 1414 / 724


def to_mask(img: Image.Image, upscale: int = 1, out_size: int = 320, pad: float = 0.06) -> Image.Image:
    g = img.convert("L")
    if upscale > 1:
        g = g.resize((g.width * upscale, g.height * upscale), Image.LANCZOS)
    # contraste net : fond blanc -> transparent, traits noirs -> opaques
    g = g.point(lambda v: 255 if v > 175 else (0 if v < 80 else int((v - 80) * 255 / 95)))
    alpha = ImageOps.invert(g)
    box = alpha.point(lambda v: 255 if v > 24 else 0).getbbox()
    alpha = alpha.crop(box)
    side = int(max(alpha.size) * (1 + 2 * pad))
    canvas = Image.new("L", (side, side), 0)
    canvas.paste(alpha, ((side - alpha.width) // 2, (side - alpha.height) // 2))
    canvas = canvas.resize((out_size, out_size), Image.LANCZOS)
    out = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    out.putalpha(canvas)
    return out


def seat_icon(size: int = 320) -> Image.Image:
    """Pictogramme « une place assise » dessiné ici (aucune source dans la charte)."""
    k = 4
    s = size * k
    img = Image.new("L", (s, s), 255)
    d = ImageDraw.Draw(img)

    def p(x, y):
        return (x * s / 100, y * s / 100)

    def line(a, b, w):
        d.line([p(*a), p(*b)], fill=0, width=int(w * s / 100))
        for c in (a, b):
            x, y = p(*c)
            r = w * s / 200
            d.ellipse([x - r, y - r, x + r, y + r], fill=0)

    x, y = p(40, 17)
    r = 9 * s / 100
    d.ellipse([x - r, y - r, x + r, y + r], fill=0)          # tête
    line((40, 32), (42, 58), 13)                                # buste
    line((42, 60), (68, 60), 12)                                # cuisses
    line((68, 60), (68, 88), 11)                                # jambes
    line((43, 38), (60, 52), 8)                                 # bras
    line((26, 24), (26, 88), 9)                                 # dossier
    line((26, 70), (74, 70), 8)                                 # assise
    line((74, 70), (74, 90), 8)                                 # pied
    return to_mask(img.resize((size, size), Image.LANCZOS), out_size=size, pad=0.1)


def bell_icon(size: int = 320) -> Image.Image:
    """Pictogramme « me rappeler mon arrêt » (cloche), dessiné ici."""
    k = 4
    s = size * k
    img = Image.new("L", (s, s), 255)
    d = ImageDraw.Draw(img)

    def p(x, y):
        return (x * s / 100, y * s / 100)

    d.pieslice([*p(24, 14), *p(76, 66)], 180, 360, fill=0)             # dôme
    d.polygon([p(24, 40), p(76, 40), p(88, 74), p(12, 74)], fill=0)     # corps évasé
    d.rounded_rectangle([*p(8, 70), *p(92, 80)], radius=int(5 * s / 100), fill=0)  # bord
    d.ellipse([*p(42, 80), *p(58, 96)], fill=0)                         # battant
    d.ellipse([*p(44, 6), *p(56, 18)], fill=0)                          # anneau
    return to_mask(img.resize((size, size), Image.LANCZOS), out_size=size, pad=0.1)


def app_icons() -> None:
    """Icônes d'installation (PWA) : astérisque rose sur violet."""
    mask = Image.open(ICONS / "logo.png").getchannel("A")
    for size in (192, 512):
        base = Image.new("RGB", (size, size), (29, 5, 169))
        glyph = mask.resize((int(size * 0.56),) * 2, Image.LANCZOS)
        pink = Image.new("RGB", glyph.size, (254, 218, 218))
        base.paste(pink, ((size - glyph.width) // 2, (size - glyph.height) // 2), glyph)
        base.save(ROOT / "static" / "img" / f"icon-{size}.png", optimize=True)


def main() -> None:
    ICONS.mkdir(parents=True, exist_ok=True)
    STOPS.mkdir(parents=True, exist_ok=True)

    # --- icônes issues de la première version (haute résolution) ---
    old = {
        "hello": "bonjour", "bus_check": "bon_bus", "ticket_buy": "acheter_billet", "help_hand": "aide",
        "repeat": "repetez", "ramp": "rampe", "front_door": "porte_avant", "more_time": "plus_de_temps",
    }
    for name, src in old.items():
        to_mask(Image.open(OLD / "pictos" / f"{src}.png")).save(ICONS / f"{name}.png", optimize=True)

    # --- icônes lues sur la charte (captures 724x1024, agrandies puis nettoyées) ---
    def scaled(box):  # coordonnées relevées sur un aperçu de 724 px de large -> taille réelle (1414 px)
        return tuple(int(v * SCALE) for v in box)

    c2 = Image.open(CHART / "2.png").convert("RGB")
    crops = {  # nom: (gauche, haut, droite, bas) dans 2.png
        "getting_out": (115, 345, 337, 470),
        "controller": (390, 340, 612, 472),
        "lost": (115, 595, 337, 728),
        "unwell": (390, 592, 612, 728),
    }
    for name, box in crops.items():
        to_mask(c2.crop(scaled(box))).save(ICONS / f"{name}.png", optimize=True)

    c1 = Image.open(CHART / "1.png").convert("RGB")
    to_mask(c1.crop(scaled((575, 168, 658, 245))), pad=0.02).save(ICONS / "logo.png", optimize=True)

    seat_icon().save(ICONS / "seat.png", optimize=True)
    bell_icon().save(ICONS / "bell.png", optimize=True)
    app_icons()

    # --- photos d'arrêts ---
    for name in ("gare", "parc", "hopital", "lac"):
        Image.open(OLD / "photos" / f"{name}.jpg").convert("RGB").resize((360, 360), Image.LANCZOS).save(
            STOPS / f"{name}.jpg", quality=84)
    c4 = Image.open(CHART / "4.png").convert("RGB")
    c4.crop(scaled((258, 400, 466, 606))).resize((360, 356), Image.LANCZOS).save(STOPS / "jardin_botanique.jpg", quality=88)
    print("OK")


if __name__ == "__main__":
    main()
