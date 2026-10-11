"""Remplace les pictogrammes d'arrêts de la ligne 701 par ceux d'un .zip (dossier « 701_stops »).

    python tools/import_stop_pictos.py "../new graphic chart/701_stops-new.zip"

Les sources sont des dessins noirs (PNG, JPG ou SVG, fonds blancs ou transparents). Chacun devient une tuile 512x512
aux coins arrondis : fond clair à la couleur de la commune (champ "color" de static/data/lines.json) et dessin bleu nuit.
Un arrêt absent du zip garde son pictogramme précédent.
"""
import io
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parent.parent
LINES = ROOT / "static" / "data" / "lines.json"
STOPS = ROOT / "static" / "img" / "stops"
DEFAULT_ZIP = ROOT.parent / "new graphic chart" / "701_stops-new.zip"

# nom du fichier du zip (sans extension, en minuscules) -> id de l'arrêt
MAPPING = {
    "allee-dorigny": "ecublens-vd-allee-de-dorigny",
    "bief": "morges-bief",
    "blancherie": "morges-blancherie",
    "blevaillares": "ecublens-vd-blevallaire",
    "bourdonette": "lausanne-bourdonnette",
    "campus-des-medias": "ecublens-vd-campus-des-medias",
    "casino": "morges-casino",
    "castolin": "st-sulpice-vd-castolin",
    "champagne": "ecublens-vd-champagne",
    "charpentiers": "morges-charpentiers",
    "eglantine": "morges-eglantine",
    "en_champagny": "st-sulpice-vd-en-champagny",
    "gare": "morges-gare",
    "morge_stjean_sud": "morges-st-jean-sud",
    "ochettaz": "st-sulpice-vd-ochettaz-ormet",
    "parc-scientifique": "st-sulpice-vd-parc-scientifique",
    "pierraz": "denges-pierraz-mur",
    "plantaz": "tolochenaz-la-plantaz",
    "prairies": "morges-la-prairie",
    "pre-fleuri": "st-sulpice-vd-pre-fleuri",
    "prelion": "morges-prelionne",
    "st_louis": "morges-st-louis",
    "taudaz": "preverenges-taudaz",
    "temple": "morges-temple",
    "village": "preverenges-village",
    "vogeaz": "morges-vogeaz",
}

TILE = 512
GLYPH = 330  # le dessin tient dans un carré de 330 px au centre de la tuile
RADIUS = 72
INK = (27, 36, 67)  # bleu nuit, comme les pictogrammes précédents
TINT = 0.86  # part de blanc mélangée à la couleur de la commune

CHROME = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
]


def render_svg(svg: bytes) -> Image.Image:
    """Rastérise un SVG (fond transparent) avec Chrome sans interface."""
    chrome = next((c for c in CHROME if os.path.exists(c)), None)
    if not chrome:
        raise SystemExit("Chrome introuvable : impossible de convertir les SVG")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "a.svg").write_bytes(svg)
        (tmp / "a.html").write_text(
            '<body style="margin:0;background:transparent"><img src="a.svg" '
            'style="display:block;width:800px;height:800px;object-fit:contain"></body>',
            encoding="utf-8",
        )
        subprocess.run(
            [chrome, "--headless", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files",
             "--force-device-scale-factor=1", "--default-background-color=00000000", "--window-size=800,800",
             "--virtual-time-budget=2000", f"--screenshot={tmp / 'a.png'}", (tmp / "a.html").as_uri()],
            check=True, capture_output=True,
        )
        return Image.open(tmp / "a.png").convert("RGBA").copy()


def ink_alpha(img: Image.Image) -> Image.Image:
    """Opacité du dessin : plus c'est sombre sur fond blanc, plus c'est opaque (les gris deviennent semi-transparents)."""
    rgba = img.convert("RGBA")
    white = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    flat = Image.alpha_composite(white, rgba).convert("L")
    dark = ImageOps.invert(flat)
    return dark.point(lambda v: 0 if v < 25 else min(255, int((v - 25) * 255 / 170)))


def tile(img: Image.Image, color: str) -> Image.Image:
    alpha = ink_alpha(img)
    box = alpha.point(lambda v: 255 if v > 60 else 0).getbbox()
    alpha = alpha.crop(box)
    w, h = alpha.size
    k = GLYPH / max(w, h)
    alpha = alpha.resize((max(1, round(w * k)), max(1, round(h * k))), Image.LANCZOS)

    base = tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))
    bg = tuple(round(c + (255 - c) * TINT) for c in base)
    out = Image.new("RGBA", (TILE, TILE), (0, 0, 0, 0))
    mask = Image.new("L", (TILE * 4, TILE * 4), 0)  # coins arrondis anticrénelés
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, TILE * 4 - 1, TILE * 4 - 1), RADIUS * 4, fill=255)
    out.paste(Image.new("RGBA", (TILE, TILE), bg + (255,)), (0, 0), mask.resize((TILE, TILE), Image.LANCZOS))
    ink = Image.new("RGBA", alpha.size, INK + (255,))
    ink.putalpha(alpha)
    out.alpha_composite(ink, ((TILE - alpha.width) // 2, (TILE - alpha.height) // 2))
    return out


def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_ZIP
    data = json.loads(LINES.read_text(encoding="utf-8"))
    colors = {}  # id -> (dossier/fichier du pictogramme, couleur)
    for line in data["lines"]:
        for stop in line["stops"]:
            if stop.get("picto"):
                colors[stop["id"]] = (stop["picto"], stop.get("color", "#2F6FD0"))

    done, missing = [], []
    with zipfile.ZipFile(src) as z:
        files = {Path(n).stem.lower(): n for n in z.namelist() if not n.endswith("/") and not Path(n).name.startswith(".")}
        for key, stop_id in MAPPING.items():
            if key not in files or stop_id not in colors:
                missing.append(stop_id)
                continue
            raw = z.read(files[key])
            img = render_svg(raw) if files[key].lower().endswith(".svg") else Image.open(io.BytesIO(raw))
            picto, color = colors[stop_id]
            tile(img, color).save(STOPS / picto, optimize=True)
            done.append(stop_id)
            print(f"ok {files[key]} -> {picto}")
    for stop_id in sorted(set(colors) - set(done)):
        print(f"gardé (absent du zip) : {stop_id}")
    print(f"{len(done)} pictogrammes remplacés")


if __name__ == "__main__":
    main()
