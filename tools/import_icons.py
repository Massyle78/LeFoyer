"""Importe les pictogrammes principaux (dossier « new graphic chart/main icons.zip ») dans static/img/icons.

Les sources sont des dessins noirs sur fond blanc : on les convertit en PNG 320x320 transparents
(le noir devient l'opacité), car l'application les utilise comme masques colorés (voir .ico dans app.css).

Usage : python tools/import_icons.py ["chemin/vers/main icons.zip"]
"""
import io
import sys
import zipfile
from pathlib import Path

from PIL import Image, ImageChops, ImageOps

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "static" / "img" / "icons"
DEFAULT_ZIP = ROOT.parent / "new graphic chart" / "main icons.zip"

# fichier du zip -> nom de l'icône dans l'application
MAPPING = {
    "bus_route.png": "bus_check",
    "exit_bus.jpg": "getting_out",
    "help.png": "help_hand",
    "lost.png": "lost",
    "repeat-transparent.png": "repeat",
    "ticket.png": "ticket_buy",
    "unwell.png": "unwell",
    "wave.png": "hello",
}

SIZE = 320
FILL = 288  # le dessin occupe au plus 288 px (marge de 16 px, comme les autres icônes) : même présence visuelle pour toutes les icônes


def to_alpha(img: Image.Image) -> Image.Image:
    """Canal alpha du dessin : noir sur blanc -> opaque ; PNG déjà transparent -> son propre alpha."""
    rgba = img.convert("RGBA")
    alpha = rgba.getchannel("A")
    if alpha.getextrema()[0] < 250:  # vraie transparence
        return alpha
    # noir sur blanc (le fond violet de repeat.png n'est pas utilisé : on prend repeat-transparent.png)
    grey = ImageOps.invert(rgba.convert("L"))
    return grey.point(lambda v: 0 if v < 12 else min(255, int((v - 12) * 255 / 200)))


def make_icon(img: Image.Image) -> Image.Image:
    alpha = to_alpha(img)
    box = alpha.point(lambda v: 255 if v > 40 else 0).getbbox()
    alpha = alpha.crop(box)
    w, h = alpha.size
    k = FILL / max(w, h)
    alpha = alpha.resize((max(1, round(w * k)), max(1, round(h * k))), Image.LANCZOS)
    out = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    black = Image.new("RGBA", alpha.size, (0, 0, 0, 255))
    black.putalpha(alpha)
    out.paste(black, ((SIZE - alpha.width) // 2, (SIZE - alpha.height) // 2), black)
    return out


def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_ZIP
    with zipfile.ZipFile(src) as z:
        names = {Path(n).name: n for n in z.namelist() if not n.endswith("/")}
        for file, icon in MAPPING.items():
            img = Image.open(io.BytesIO(z.read(names[file])))
            make_icon(img).save(DEST / f"{icon}.png", optimize=True)
            print(f"ok {file} -> {icon}.png")


if __name__ == "__main__":
    main()

