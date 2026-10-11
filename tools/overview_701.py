"""Génère docs/ligne-701.png : la planche de tous les pictogrammes d'arrêts de la ligne 701 (pour le README).

    python tools/overview_701.py
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
LINES = json.loads((ROOT / "static" / "data" / "lines.json").read_text(encoding="utf-8"))["lines"]
OUT = ROOT / "docs" / "ligne-701.png"

FONTS = [r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\arialbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
SMALL = [r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]


def font(paths, size):
    for path in paths:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def main() -> None:
    stops, seen = [], set()
    for line in LINES:
        if line["number"].startswith("701"):
            for stop in line["stops"]:
                if stop["id"] not in seen and stop.get("picto"):
                    seen.add(stop["id"])
                    stops.append(stop)

    cols, tile, gap, label_h, margin, top = 7, 190, 22, 62, 30, 90
    rows = -(-len(stops) // cols)
    width = margin * 2 + cols * tile + (cols - 1) * gap
    height = top + rows * (tile + label_h) + (rows - 1) * gap + margin
    sheet = Image.new("RGB", (width, height), (254, 218, 218))  # rose de la charte
    draw = ImageDraw.Draw(sheet)
    draw.text((margin, 26), "Ligne 701 : Tolochenaz - Morges - Préverenges - Denges - St-Sulpice - Ecublens - Lausanne",
              font=font(FONTS, 26), fill=(29, 5, 169))

    for i, stop in enumerate(stops):
        x = margin + (i % cols) * (tile + gap)
        y = top + (i // cols) * (tile + label_h + gap)
        picto = Image.open(ROOT / "static" / "img" / "stops" / stop["picto"]).convert("RGBA").resize((tile, tile), Image.LANCZOS)
        draw.rounded_rectangle((x - 6, y - 6, x + tile + 6, y + tile + label_h - 8), 22, fill=(255, 255, 255), outline=stop["color"], width=4)
        sheet.paste(picto, (x, y), picto)
        draw.text((x + tile / 2, y + tile + 8), stop["commune"], font=font(SMALL, 15), fill=(90, 90, 110), anchor="mt")
        name = stop["name"]
        size = 22
        while draw.textlength(name, font=font(FONTS, size)) > tile - 8 and size > 13:
            size -= 1
        draw.text((x + tile / 2, y + tile + 28), name, font=font(FONTS, size), fill=(29, 5, 169), anchor="mt")

    sheet.save(OUT, optimize=True)
    print(f"ok {OUT} ({len(stops)} arrêts)")


if __name__ == "__main__":
    main()

