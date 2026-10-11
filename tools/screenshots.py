"""Génère les captures d'écran du README (docs/screenshots/*.png) avec Chrome ou Edge en mode « headless ».

    python tools/screenshots.py                       # depuis le site déployé
    python tools/screenshots.py http://localhost:5000  # depuis le serveur local (python app.py)

Nécessite Pillow (déjà utilisé par tools/build_assets.py) et Chrome ou Edge installé.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import quote

from PIL import Image

BASE = (sys.argv[1] if len(sys.argv) > 1 else "https://massyle78.github.io/LeFoyer").rstrip("/")
OUT = Path(__file__).resolve().parent.parent / "docs" / "screenshots"
WIDTH, HEIGHT, SCALE = 500, 860, 2  # Chrome ne descend pas sous ~500 px de large ; on rogne ensuite à 480 px (largeur max de l'appli)

BROWSERS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "google-chrome",
    "chromium",
    "microsoft-edge",
]


def p(**kw):
    return quote(json.dumps(kw, separators=(",", ":")))


# (nom du fichier, adresse, durée d'attente virtuelle en ms)
SHOTS = [
    ("01-lines", "/?lang=en", 5000),
    ("02-home", "/?lang=en&line=8", 5000),
    ("03-picker", f"/?lang=en&line=8&view=picker&p={p(need='check')}", 6000),
    ("04-answer-yes", f"/?lang=en&line=8&view=answer&p={p(stop='hopital', yes=True)}", 5000),
    ("05-answer-no", f"/?lang=en&line=8&view=answer&p={p(stop='gare', yes=False)}", 5000),
    ("06-help", f"/?lang=en&line=8&view=help", 5000),
    ("07-ramp-card", f"/?lang=en&line=8&view=card&p={p(phrase='ramp', icon='ramp', stop='parc')}", 5000),
    ("08-mystop-calm", "/?lang=en&line=8&dest=lac&view=mystop", 5000),
    ("09-alarm-soon", "/?lang=en&line=8&dest=hopital&view=mystop&speed=2", 4800),
    ("10-alarm-now", "/?lang=en&line=8&dest=hopital&view=mystop&speed=2", 7500),
    ("11-settings", "/?lang=en&line=8&view=settings", 5000),
    ("12-lines-fr", "/?lang=fr", 5000),
    ("13-demo", "/?lang=en&demo=2&autostart=1", 9000),
]


def find_browser():
    for candidate in BROWSERS:
        path = candidate if os.path.isabs(candidate) else shutil.which(candidate)
        if path and os.path.exists(path):
            return path
    sys.exit("Chrome ou Edge introuvable.")


def shoot(browser, name, path, budget):
    OUT.mkdir(parents=True, exist_ok=True)
    raw = Path(tempfile.gettempdir()) / f"bb-{name}.png"
    profile = tempfile.mkdtemp(prefix="bb-profile-")  # profil vierge : pas de réglages mémorisés
    cmd = [
        browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
        f"--user-data-dir={profile}", f"--force-device-scale-factor={SCALE}",
        f"--window-size={WIDTH},{HEIGHT}", f"--virtual-time-budget={budget}",
        f"--screenshot={raw}", BASE + path,
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=90)
    shutil.rmtree(profile, ignore_errors=True)
    image = Image.open(raw).convert("RGB")
    margin = (image.width - 480 * SCALE) // 2
    image.crop((margin, 0, image.width - margin, image.height)).save(OUT / f"{name}.png", optimize=True)
    raw.unlink(missing_ok=True)
    print("ok", name)


if __name__ == "__main__":
    browser = find_browser()
    only = sys.argv[2:]  # ex. : python tools/screenshots.py http://localhost:5000 09-alarm-soon
    for shot in SHOTS:
        if not only or shot[0] in only:
            shoot(browser, *shot)
