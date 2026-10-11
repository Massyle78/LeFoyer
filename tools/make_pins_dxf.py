"""Génère merch/bus-buddy-pins.dxf : une planche de pin's, de porte-clés et de petits souvenirs Bus Buddy pour la découpe laser.
(6 pin's, 6 porte-clés, 10 mini badges Ø 25 mm et 8 petites formes : Le Foyer / HackaHealth / Bus Buddy / EPFL / équipe)

    python tools/make_pins_dxf.py                  # planche 300 x 200 mm
    python tools/make_pins_dxf.py --sheet 400x300  # autre taille de plaque
    python tools/make_pins_dxf.py --font "C:/Windows/Fonts/arialbd.ttf"

Calques du DXF (unités : millimètres, origine en bas à gauche de la planche) :
  CUT      rouge  : contours à DÉCOUPER (et trous de porte-clés)
  ENGRAVE  bleu   : dessins à GRAVER (contours fermés : à remplir dans le logiciel du laser pour une gravure pleine)
  SHEET    gris   : cadre de la planche (repère, ne pas découper)
  LABELS   noir   : noms des modèles et légende (ne pas découper)

Les textes sont convertis en contours (aucune police nécessaire pour ouvrir le fichier).
Dépendances : pip install ezdxf shapely fonttools matplotlib
"""
import argparse
import math
from pathlib import Path

import ezdxf
from ezdxf import units
from fontTools.pens.basePen import decomposeQuadraticSegment
from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont
from shapely import affinity
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "merch"
FONT_CANDIDATES = [r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\segoeuib.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]

# --- réglages (mm) --------------------------------------------------------------------------------------------
BORDER = 1.7  # liseré gravé à l'intérieur du contour
TAB_R, HOLE_R = 4.4, 1.8  # anneau du porte-clés : rayon extérieur, rayon du trou (Ø 3,6)
GAP, ROW_GAP, MARGIN = 5.0, 11.0, 8.0


# --- texte -> contours ------------------------------------------------------------------------------------------
class Lettering:
    def __init__(self, font_path: str):
        self.font = TTFont(font_path)
        self.glyphs = self.font.getGlyphSet()
        self.cmap = self.font.getBestCmap()
        self.em = self.font["head"].unitsPerEm
        self.cap = getattr(self.font["OS/2"], "sCapHeight", 0) or 0.716 * self.em
        self.min_cap = float("inf")  # plus petite hauteur de capitale effectivement utilisée (contrôle de lisibilité)

    def _contours(self, name: str):
        pen = RecordingPen()
        self.glyphs[name].draw(pen)
        contours, current = [], []
        for op, args in pen.value:
            if op == "moveTo":
                current = [args[0]]
            elif op == "lineTo":
                current.append(args[0])
            elif op == "qCurveTo":
                start = current[-1]
                points = list(args)
                if points[-1] is None:  # contour sans point sur la courbe : rare, ignoré
                    continue
                for (c, end) in decomposeQuadraticSegment(points):
                    for i in range(1, 9):
                        t = i / 8
                        current.append(((1 - t) ** 2 * start[0] + 2 * (1 - t) * t * c[0] + t * t * end[0],
                                        (1 - t) ** 2 * start[1] + 2 * (1 - t) * t * c[1] + t * t * end[1]))
                    start = end
            elif op == "curveTo":
                start = current[-1]
                c1, c2, end = args
                for i in range(1, 11):
                    t = i / 10
                    current.append(tuple((1 - t) ** 3 * start[k] + 3 * (1 - t) ** 2 * t * c1[k] + 3 * (1 - t) * t * t * c2[k] + t ** 3 * end[k] for k in (0, 1)))
            elif op in ("closePath", "endPath"):
                if len(current) > 2:
                    contours.append(current)
                current = []
        return contours

    def _glyph(self, name: str):
        shape = None
        for contour in self._contours(name):
            poly = Polygon(contour).buffer(0)
            shape = poly if shape is None else shape.symmetric_difference(poly)  # un contour dans un autre = un trou
        return shape

    def text(self, s: str, cap_height: float, center=(0.0, 0.0), max_width: float | None = None, track: float = 0.0):
        """Texte en contours (polygones avec trous), centré sur `center`, lettres de `cap_height` mm de haut.
        `track` : espacement supplémentaire entre les lettres (mm)."""
        scale = cap_height / self.cap
        x, pieces = 0.0, []
        for ch in s:
            name = self.cmap.get(ord(ch))
            if name is None:
                continue
            shape = self._glyph(name)
            if shape is not None and not shape.is_empty:
                pieces.append(affinity.translate(shape, xoff=x))
            x += self.glyphs[name].width + track / scale
        geom = affinity.scale(unary_union(pieces), xfact=scale, yfact=scale, origin=(0, 0))
        minx, miny, maxx, maxy = geom.bounds
        if max_width and (maxx - minx) > max_width:
            k = max_width / (maxx - minx)
            geom = affinity.scale(geom, xfact=k, yfact=k, origin=(0, 0))
            minx, miny, maxx, maxy = geom.bounds
            cap_height *= k
        self.min_cap = min(self.min_cap, cap_height)
        return affinity.translate(geom, xoff=center[0] - (minx + maxx) / 2, yoff=center[1] - (miny + maxy) / 2)

    def arc_text(self, s: str, cap_height: float, radius: float, top: bool, track: float = 0.0):
        """Texte courbe autour de l'origine. `top=True` : en haut, lisible de gauche à droite, pieds des lettres au rayon
        `radius`, sommets vers l'extérieur. `top=False` : en bas, lisible de gauche à droite, pieds au rayon `radius`
        (extérieur), sommets vers le centre. Renvoie (géométrie, demi-ouverture angulaire en degrés)."""
        scale = cap_height / self.cap
        x, items = 0.0, []
        for ch in s:
            name = self.cmap.get(ord(ch))
            if name is None:
                continue
            adv = self.glyphs[name].width * scale
            shape = self._glyph(name)
            if shape is not None and not shape.is_empty:
                items.append((affinity.scale(shape, xfact=scale, yfact=scale, origin=(0, 0)), x + adv / 2, adv / 2))
            x += adv + track
        total = x - track
        out = []
        for shape, xc, half_adv in items:
            off = math.degrees((xc - total / 2) / radius)
            phi = math.radians(90 - off if top else 270 + off)
            rot = math.degrees(phi) - (90 if top else 270)
            g = affinity.rotate(affinity.translate(shape, -half_adv, 0), rot, origin=(0, 0))
            out.append(affinity.translate(g, radius * math.cos(phi), radius * math.sin(phi)))
        self.min_cap = min(self.min_cap, cap_height)
        return unary_union(out), math.degrees(total / 2 / radius)


# --- formes de base ------------------------------------------------------------------------------------------------
def rrect(cx, cy, w, h, r):
    return box(cx - w / 2 + r, cy - h / 2 + r, cx + w / 2 - r, cy + h / 2 - r).buffer(r, quad_segs=12)


def circle(cx, cy, r):
    return Point(cx, cy).buffer(r, quad_segs=32)


def asterisk(cx, cy, r, width, arms=6):
    """L'astérisque du logo Bus Buddy : `arms` branches arrondies."""
    bars = [affinity.rotate(LineString([(-r, 0), (r, 0)]), 90 + k * 180 / (arms // 2), origin=(0, 0)) for k in range(arms // 2)]
    return affinity.translate(unary_union([b.buffer(width / 2, quad_segs=8) for b in bars]), cx, cy)


def bus_front(cx, cy, w):
    """Pictogramme d'un bus vu de face (contours à graver)."""
    h = 0.88 * w
    parts = [
        rrect(cx, cy, w, h, 0.18 * w),  # caisse
        rrect(cx, cy + 0.34 * h, 0.4 * w, 0.12 * h, 0.03 * w),  # girouette
        rrect(cx, cy + 0.07 * h, 0.76 * w, 0.34 * h, 0.05 * w),  # pare-brise
        circle(cx - 0.3 * w, cy - 0.28 * h, 0.075 * w),  # phares
        circle(cx + 0.3 * w, cy - 0.28 * h, 0.075 * w),
        rrect(cx, cy - 0.28 * h, 0.26 * w, 0.07 * h, 0.02 * w),  # calandre
        rrect(cx - 0.3 * w, cy - 0.5 * h - 0.03 * w, 0.16 * w, 0.12 * w, 0.02 * w),  # roues
        rrect(cx + 0.3 * w, cy - 0.5 * h - 0.03 * w, 0.16 * w, 0.12 * w, 0.02 * w),
    ]
    return parts


def smooth(shape, r=1.2):
    """Raccords arrondis entre les pièces d'une forme (retire les angles vifs, bouche les creux étroits)."""
    return shape.buffer(r, quad_segs=12).buffer(-r, quad_segs=12)


def round_corners(shape, r=1.5):
    return shape.buffer(-r, quad_segs=12).buffer(r, quad_segs=12)


def top_at(shape, x):
    return shape.intersection(LineString([(x, -500), (x, 500)])).bounds[3]


# --- les modèles -------------------------------------------------------------------------------------------------------
# chaque modèle : (nom, contour à découper, liste de géométries à graver, abscisse de l'anneau de porte-clés)
def style_round(L, d=42.0):
    r = d / 2
    outline = circle(0, 0, r)
    eng = [outline.buffer(-BORDER), asterisk(0, 13.4, 3.9, 2.2), *bus_front(0, -0.9, 14.0), L.text("BUS BUDDY", 2.8, (0, -12.4), max_width=24)]
    return "A - ROUND", outline, eng


def style_bus(L):
    body = rrect(0, 3.0, 50, 22, 4.5)
    wheels = [circle(-14, -8, 5.2), circle(14, -8, 5.2)]
    outline = smooth(unary_union([body, *wheels]), 1.0)
    windows = [rrect(x + 3, 7.6, 6.2, 6.2, 1.0) for x in (-21.5 + k * 7.7 for k in range(4))]
    eng = [
        outline.buffer(-BORDER),
        *windows,
        rrect(11.6, 2.8, 5.8, 15.4, 0.8),  # porte
        rrect(20.2, 6.9, 7.0, 7.2, 1.2),  # pare-brise
        circle(23.0, -2.2, 1.1),  # phare
        *[circle(x, -8, 2.3) for x in (-14, 14)],  # moyeux
        L.text("701", 4.6, (-9.0, -2.4), max_width=14),
    ]
    return "B - BUS", outline, eng


def style_house(L):
    shape = unary_union([box(-15, -21, 15, 6), Polygon([(-21.5, 4.5), (21.5, 4.5), (0, 22.5)]), box(8.5, 12, 13.5, 21)])
    outline = round_corners(shape, 1.6)
    eng = [outline.buffer(-BORDER), asterisk(0, 11.2, 4.0, 2.2), *bus_front(0, -6.0, 13), L.text("LE FOYER", 2.4, (0, -17.0), max_width=22)]
    return "C - FOYER", outline, eng


def style_heart(L):
    pts = []
    for i in range(240):
        t = 2 * math.pi * i / 240
        pts.append((16 * math.sin(t) ** 3 * 1.25, (13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)) * 1.25))
    outline = Polygon(pts)
    eng = [outline.buffer(-BORDER), asterisk(0, -0.6, 6.0, 2.8), L.text("701", 3.2, (0, -10.4), max_width=9)]
    return "D - HEART", outline, eng


def style_sign(L):
    shape = unary_union([circle(0, 5, 17), box(-3.2, -24, 3.2, 6)])
    outline = smooth(round_corners(shape, 1.0), 1.5)
    eng = [circle(0, 5, 17 - BORDER), L.text("701", 8.6, (0, 8.2), max_width=22), asterisk(0, -3.4, 3.4, 1.9)]
    return "E - STOP SIGN", outline, eng


def style_bubble(L):
    shape = unary_union([rrect(0, 2, 42, 27, 9), Polygon([(-13, -8), (-3, -8), (-15.5, -19)])])
    outline = smooth(shape, 1.2)
    eng = [outline.buffer(-BORDER), L.text("Hello !", 6.0, (0, 0.8), max_width=30), asterisk(0, 9.0, 2.6, 1.5)]
    return "F - HELLO", outline, eng


# --- petits souvenirs : identité du projet (Le Foyer, HackaHealth, Bus Buddy, EPFL, équipe) ---------------------------
# Règles de gravure : hauteur de capitale >= MIN_CAP, liseré à MINI_BORDER du bord, rien ne touche le liseré (>= 0,4 mm).
# Le nom s'écrit « HackaHealth » (site hackahealth.ch) ; en capitales gravées : HACKAHEALTH.
MIN_CAP, MINI_BORDER, MINI_R = 2.2, 1.4, 12.5
YEAR = "2026"


def heart(cx, cy, w):
    pts = [(16 * math.sin(t) ** 3, 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
           for t in (2 * math.pi * i / 240 for i in range(240))]
    shape = Polygon(pts)
    minx, miny, maxx, maxy = shape.bounds
    shape = affinity.translate(shape, -(minx + maxx) / 2, -(miny + maxy) / 2)
    return affinity.translate(affinity.scale(shape, w / (maxx - minx), w / (maxx - minx), origin=(0, 0)), cx, cy)


def health_cross(cx, cy, size, arm):
    """Croix « santé » (plus) aux bouts arrondis, `size` = largeur totale, `arm` = épaisseur des branches."""
    return unary_union([rrect(cx, cy, size, arm, arm * 0.25), rrect(cx, cy, arm, size, arm * 0.25)])


def house_icon(cx, cy, w):
    """Maison simple (toit + corps) : renvoie [contour, porte]."""
    body_w, body_h, roof_h = 0.74 * w, 0.44 * w, 0.42 * w
    body = box(cx - body_w / 2, cy - (body_h + roof_h) / 2, cx + body_w / 2, cy - (body_h + roof_h) / 2 + body_h)
    top = cy - (body_h + roof_h) / 2 + body_h
    roof = Polygon([(cx - w / 2, top - 0.02 * w), (cx + w / 2, top - 0.02 * w), (cx, top + roof_h)])
    door = rrect(cx, cy - (body_h + roof_h) / 2 + 0.17 * w, 0.2 * w, 0.34 * w, 0.02 * w)
    return [round_corners(unary_union([body, roof]), 0.25), door]


def mini_round():
    outline = circle(0, 0, MINI_R)
    return outline, [outline.buffer(-MINI_BORDER)]


def ring_dots(eng, half_top, half_bottom, radius=9.35):
    """Deux petits points entre l'arc du haut et celui du bas."""
    for ang in (180 + (half_top - half_bottom) / 2, (half_bottom - half_top) / 2):
        eng.append(circle(radius * math.cos(math.radians(ang)), radius * math.sin(math.radians(ang)), 0.6))


def mini_buddy(L):
    outline, eng = mini_round()
    eng += [asterisk(0, 5.6, 3.4, 1.9), L.text("BUS", 2.6, (0, -0.8), track=0.2), L.text("BUDDY", 2.6, (0, -5.0), track=0.2)]
    return "M01 BUS BUDDY", outline, eng


def mini_ring_buddy(L):
    outline, eng = mini_round()
    top, ht = L.arc_text("BUS BUDDY", 2.3, 8.2, True, track=0.1)
    bottom, hb = L.arc_text("LE FOYER", 2.3, 10.5, False, track=0.25)
    eng += [top, bottom, asterisk(0, 0, 4.0, 2.1)]
    ring_dots(eng, ht, hb)
    return "M02 RING BUDDY", outline, eng


def mini_foyer_ring(L):
    outline, eng = mini_round()
    top, ht = L.arc_text("TEAM", 2.4, 8.1, True, track=0.3)
    bottom, hb = L.arc_text("LE FOYER", 2.4, 10.5, False, track=0.25)
    eng += [top, bottom, *house_icon(0, 0.2, 10.5)]
    ring_dots(eng, ht, hb)
    return "M03 FOYER", outline, eng


def mini_health_text(L):
    outline, eng = mini_round()
    eng += [*[heart(0, 6.4, 6.2)], L.text("HACKA", 2.5, (0, 1.2), track=0.2), L.text("HEALTH", 2.5, (0, -2.6), track=0.2),
            L.text(YEAR, 2.3, (0, -6.7), track=0.3)]
    return "M04 HEALTH", outline, eng


def mini_ring_health(L):
    outline, eng = mini_round()
    top, ht = L.arc_text("HACKAHEALTH", 2.2, 8.3, True)
    bottom, hb = L.arc_text("EPFL " + YEAR, 2.2, 10.5, False, track=0.25)
    eng += [top, bottom, health_cross(0, 0, 8.4, 3.0)]
    return "M05 RING HEALTH", outline, eng


def mini_epfl(L):
    outline, eng = mini_round()
    eng += [asterisk(0, 7.2, 2.4, 1.4), L.text("EPFL", 5.0, (0, 0.6), track=0.4), L.text(YEAR, 2.4, (0, -6.0), track=0.3)]
    return "M06 EPFL", outline, eng


def mini_team_bus(L):
    outline, eng = mini_round()
    eng += [*bus_front(0, 5.6, 9.6), L.text("TEAM", 3.0, (0, -1.6), track=0.3), L.text("701", 2.6, (0, -6.2), track=0.3)]
    return "M07 TEAM 701", outline, eng


def mini_ring_bus(L):
    outline, eng = mini_round()
    top, ht = L.arc_text("HACKAHEALTH", 2.2, 8.3, True)
    bottom, hb = L.arc_text("BUS BUDDY", 2.2, 10.5, False, track=0.25)
    eng += [top, bottom, *bus_front(0, 0.2, 9.2)]
    return "M08 RING BUS", outline, eng


def mini_hacka_stack(L):
    outline, eng = mini_round()
    eng += [L.text("HACKA", 3.0, (0, 4.5), track=0.2), L.text("HEALTH", 3.0, (0, -0.2), track=0.2), L.text(YEAR, 2.4, (0, -5.4), track=0.3)]
    return "M09 HACKA 26", outline, eng


def mini_team_foyer(L):
    outline, eng = mini_round()
    eng += [L.text("TEAM", 3.6, (0, 4.6), track=0.3), L.text("LE FOYER", 2.4, (0, -0.6), track=0.15), asterisk(0, -6.0, 2.3, 1.3)]
    return "M10 TEAM FOYER", outline, eng


def shield_shape(w=22.0, h=25.0):
    hw, top = w / 2, h / 2
    pts = [(-hw, top), (hw, top), (hw, 0.0)]
    p0, p1, p2, p3 = (hw, 0.0), (hw, -0.52 * h / 2 * 1.0), (0.4 * hw, -0.8 * h / 2), (0.0, -top)
    for i in range(1, 25):
        t = i / 24
        pts.append(tuple((1 - t) ** 3 * p0[k] + 3 * (1 - t) ** 2 * t * p1[k] + 3 * (1 - t) * t * t * p2[k] + t ** 3 * p3[k] for k in (0, 1)))
    pts += [(-x, y) for x, y in reversed(pts[2:-1])]
    return round_corners(Polygon(pts), 1.6)


def mini_shield_epfl(L):
    outline = shield_shape()
    eng = [outline.buffer(-MINI_BORDER), L.text("EPFL", 3.6, (0, 5.9), track=0.3), asterisk(0, -0.4, 3.0, 1.6),
           L.text(YEAR, 2.3, (0, -6.4), track=0.2)]
    return "S1 SHIELD EPFL", outline, eng


def mini_shield_hacka(L):
    outline = shield_shape()
    eng = [outline.buffer(-MINI_BORDER), L.text("HACKA", 2.4, (0, 7.2), track=0.15), L.text("HEALTH", 2.4, (0, 3.0), track=0.15),
           heart(0, -3.4, 6.6)]
    return "S2 SHIELD HEALTH", outline, eng


def mini_heart_team(L):
    outline = heart(0, 0, 27.0)
    eng = [outline.buffer(-MINI_BORDER), L.text("TEAM", 2.6, (0, 2.6), track=0.3), asterisk(0, -2.9, 2.2, 1.4)]
    return "H1 HEART TEAM", outline, eng


def mini_heart_buddy(L):
    outline = heart(0, 0, 27.0)
    eng = [outline.buffer(-MINI_BORDER), L.text("BUS", 2.3, (0, 3.2), track=0.3), L.text("BUDDY", 2.3, (0, -0.4), track=0.2),
           asterisk(0, -5.0, 1.7, 1.0)]
    return "H2 HEART BUDDY", outline, eng


def hexagon(r=13.0):
    return round_corners(Polygon([(r * math.cos(math.radians(60 * k)), r * math.sin(math.radians(60 * k))) for k in range(6)]), 2.0)


def mini_hex_health(L):
    outline = hexagon()
    eng = [outline.buffer(-MINI_BORDER), health_cross(0, 6.2, 5.0, 1.8), L.text("HACKA", 2.6, (0, 1.0), track=0.2),
           L.text("HEALTH", 2.6, (0, -3.0), track=0.2), L.text(YEAR, 2.2, (0, -6.9), track=0.3)]
    return "X1 HEX HEALTH", outline, eng


def mini_hex_foyer(L):
    outline = hexagon()
    eng = [outline.buffer(-MINI_BORDER), *house_icon(0, 4.9, 8.0), L.text("LE", 2.4, (0, -1.0), track=0.2),
           L.text("FOYER", 2.8, (0, -5.0), track=0.2)]
    return "X2 HEX FOYER", outline, eng


def _tag(L, line1, cap1, line2, cap2):
    w, h = 42.0, 17.0
    outline = rrect(0, 0, w, h, 5.0)
    hx = -w / 2 + 5.2
    cx = (hx + HOLE_R + 1.6 + w / 2 - MINI_BORDER - 1.0) / 2
    eng = [outline.buffer(-MINI_BORDER), L.text(line1, cap1, (cx, 2.7), track=0.2), L.text(line2, cap2, (cx, -3.0), track=0.2)]
    return outline, [g.difference(circle(hx, 0, HOLE_R + 1.0)) for g in eng], [circle(hx, 0, HOLE_R)]


def mini_tag_foyer(L):
    outline, eng, holes = _tag(L, "LE FOYER", 3.6, "HACKAHEALTH", 2.4)
    return "T1 TAG FOYER", outline, eng, holes


def mini_tag_buddy(L):
    outline, eng, holes = _tag(L, "BUS BUDDY", 3.2, "EPFL " + YEAR, 2.4)
    return "T2 TAG BUDDY", outline, eng, holes


# --- assemblage -------------------------------------------------------------------------------------------------------------
def with_keyring(name, outline, eng):
    """Version porte-clés : un anneau avec un trou au sommet (le trou est découpé)."""
    x = 0.0
    cy = top_at(outline, x) + TAB_R - 2.0
    tab = circle(x, cy, TAB_R)
    merged = smooth(unary_union([outline, tab]), 1.2)
    hole = circle(x, cy, HOLE_R)
    eng = [g.difference(circle(x, cy, HOLE_R + 1.0)) for g in eng]  # pas de gravure qui frôle le trou
    return name + " + KEYRING", merged, eng, [hole]


def place(piece, x, y):
    """Déplace un modèle : coin bas-gauche de son contour en (x, y)."""
    name, outline, eng, holes = piece
    minx, miny, _, _ = outline.bounds
    move = lambda g: affinity.translate(g, x - minx, y - miny)
    return name, move(outline), [move(g) for g in eng], [move(g) for g in holes]


def rings(geom):
    """Contours fermés d'une géométrie (polygones : extérieur et trous ; lignes : telles quelles)."""
    if geom.is_empty:
        return
    if isinstance(geom, (Polygon,)):
        yield list(geom.exterior.coords)[:-1]
        for hole in geom.interiors:
            yield list(hole.coords)[:-1]
    elif isinstance(geom, (MultiPolygon,)) or hasattr(geom, "geoms"):
        for g in geom.geoms:
            yield from rings(g)


def build(sheet_w: float, sheet_h: float, font_path: str):
    L = Lettering(font_path)
    singles = [style_round(L), style_bus(L), style_house(L), style_heart(L), style_sign(L), style_bubble(L)]
    pins = [(n, o, e, []) for n, o, e in singles]
    keyrings = [with_keyring(n, o, e) for n, o, e in singles]
    L.min_cap = float("inf")
    badges = [(*f(L), []) for f in (mini_buddy, mini_ring_buddy, mini_foyer_ring, mini_health_text, mini_ring_health,
                                     mini_epfl, mini_team_bus, mini_ring_bus, mini_hacka_stack, mini_team_foyer)]
    extras = [mini_tag_foyer(L), mini_shield_epfl(L) + ([],), mini_heart_team(L) + ([],), mini_hex_health(L) + ([],),
              mini_hex_foyer(L) + ([],), mini_heart_buddy(L) + ([],), mini_shield_hacka(L) + ([],), mini_tag_buddy(L)]
    if L.min_cap < MIN_CAP - 1e-6:
        raise SystemExit(f"texte trop petit pour la gravure : capitales de {L.min_cap:.2f} mm (minimum {MIN_CAP} mm)")

    rows = []
    for row in (pins, keyrings, badges, extras):
        gap = GAP if row is pins or row is keyrings else 3.0
        total = sum(p[1].bounds[2] - p[1].bounds[0] for p in row) + gap * (len(row) - 1)
        height = max(p[1].bounds[3] - p[1].bounds[1] for p in row)
        rows.append((row, gap, total, height))

    needed = sum(r[3] for r in rows) + ROW_GAP * (len(rows) - 1) + 2 * MARGIN
    if needed > sheet_h or max(r[2] for r in rows) + 2 * MARGIN > sheet_w:
        raise SystemExit(f"la planche {sheet_w:g}x{sheet_h:g} mm est trop petite (il faut au moins "
                         f"{max(r[2] for r in rows) + 2 * MARGIN:.0f}x{needed:.0f} mm)")
    placed = []
    y = sheet_h - MARGIN - (sheet_h - needed) / 2
    for row, gap, total, height in rows:
        y -= height
        x = (sheet_w - total) / 2
        for piece in row:
            w = piece[1].bounds[2] - piece[1].bounds[0]
            h = piece[1].bounds[3] - piece[1].bounds[1]
            placed.append(place(piece, x, y + (height - h) / 2))
            x += w + gap
        y -= ROW_GAP
    return placed


def write_dxf(placed, sheet_w, sheet_h, path: Path, label_font: Lettering):
    doc = ezdxf.new("R2000", setup=True)
    doc.units = units.MM
    doc.header["$MEASUREMENT"] = 1
    for name, color in (("CUT", 1), ("ENGRAVE", 5), ("SHEET", 8), ("LABELS", 250)):
        doc.layers.add(name, color=color)
    msp = doc.modelspace()

    def poly(points, layer):
        msp.add_lwpolyline(points, close=True, dxfattribs={"layer": layer})

    poly([(0, 0), (sheet_w, 0), (sheet_w, sheet_h), (0, sheet_h)], "SHEET")
    cuts = 0
    for name, outline, eng, holes in placed:
        for ring in rings(outline):
            poly(ring, "CUT")
        for hole in holes:
            for ring in rings(hole):
                poly(ring, "CUT")
        for geom in eng:
            for ring in rings(geom):
                poly(ring, "ENGRAVE")
        cuts += 1
        minx, miny, maxx, maxy = outline.bounds
        width = maxx - minx
        for ring in rings(label_font.text(name, 1.8, ((minx + maxx) / 2, miny - 4.2), max_width=width + 6 if width > 30 else width)):
            poly(ring, "LABELS")
    legend = f"BUS BUDDY pins - sheet {sheet_w:g} x {sheet_h:g} mm - CUT = red (cut through) / ENGRAVE = blue (fill) - 3 mm acrylic or plywood"
    for ring in rings(label_font.text(legend, 1.8, (sheet_w / 2, 1.9), max_width=sheet_w - 20)):
        poly(ring, "LABELS")
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(path)
    return cuts


def preview(dxf_path: Path, png_path: Path, dpi: int = 110):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from ezdxf.addons.drawing import Frontend, RenderContext
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend

    doc = ezdxf.readfile(dxf_path)
    fig = plt.figure(figsize=(15, 10), dpi=int(dpi))
    ax = fig.add_axes([0, 0, 1, 1])
    ctx = RenderContext(doc)
    ctx.set_current_layout(doc.modelspace())
    Frontend(ctx, MatplotlibBackend(ax)).draw_layout(doc.modelspace(), finalize=True)
    ax.set_facecolor("white")
    fig.savefig(png_path, facecolor="white")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sheet", default="300x200", help="taille de la planche en mm (LxH)")
    parser.add_argument("--font", help="police TTF grasse pour les textes")
    parser.add_argument("--out", type=Path, default=OUT / "bus-buddy-pins.dxf")
    args = parser.parse_args()
    sheet_w, sheet_h = (float(v) for v in args.sheet.lower().split("x"))
    font = args.font or next((f for f in FONT_CANDIDATES if Path(f).exists()), None)
    if not font:
        raise SystemExit("aucune police trouvée : indiquer --font chemin.ttf")
    placed = build(sheet_w, sheet_h, font)
    count = write_dxf(placed, sheet_w, sheet_h, args.out, Lettering(font))
    preview(args.out, args.out.with_suffix(".png"))
    print(f"ok {args.out} : {count} pièces sur {sheet_w:g} x {sheet_h:g} mm (aperçu : {args.out.with_suffix('.png').name})")


if __name__ == "__main__":
    main()
