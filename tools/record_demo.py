"""Enregistre la démo en vidéo MP4 (H.264, sans le son) avec Chrome sans interface.

    python tools/record_demo.py http://localhost:5000            # diapo 1920x1080 : photos | téléphone | QR code
    python tools/record_demo.py http://localhost:5000 --phone    # téléphone seul (780x1600)
    python tools/record_demo.py http://localhost:5000 --lang fr --intro it   # version française : bonjour en italien, puis français

La démo courte (`tour=pitch`, environ une minute) est jouée une seule fois. La voix n'est pas enregistrée : la démo
affiche un bandeau explicatif à chaque étape.

Principe : Chrome joue la démo dans un téléphone et on capture ses images (Page.startScreencast). La capture d'une page
pleine HD est trop lente en Chrome sans carte graphique (2 images/s) ; pour la diapo, on enregistre donc le téléphone seul,
puis on assemble chaque image de la vidéo : la page de présentation est photographiée « à vide » (zones vertes) avec
?compose=…, et on y colle le téléphone et les photos de l'équipe (fondu enchaîné), à 30 images/s.
Dépendances : pip install websocket-client av pillow numpy
"""
import argparse
import base64
import io
import json
import os
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

import av
import numpy as np
import websocket
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
CHROME = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
]
FPS = 30
PORT = 9333
SLIDE_EVERY, SLIDE_FADE = 5.5, 1.4  # même rythme que le diaporama de static/js/present.js
KEY = np.array([0, 255, 0], dtype=np.float32)  # vert des zones « à remplir »


class Cdp:
    """Mini client du protocole Chrome DevTools : commandes + réception des images de l'écran."""

    def __init__(self, url: str):
        self.ws = websocket.create_connection(url, timeout=1.0, suppress_origin=True)
        self.next_id = 0
        self.frames: list[tuple[float, bytes]] = []

    def _handle(self, message: dict) -> None:
        if message.get("method") == "Page.screencastFrame":
            params = message["params"]
            self.frames.append((params["metadata"]["timestamp"], base64.b64decode(params["data"])))
            self.send("Page.screencastFrameAck", {"sessionId": params["sessionId"]}, wait=False)

    def send(self, method: str, params: dict | None = None, wait: bool = True):
        self.next_id += 1
        mid = self.next_id
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        while wait:
            try:
                message = json.loads(self.ws.recv())
            except websocket.WebSocketTimeoutException:
                continue
            if message.get("id") == mid:
                return message.get("result")
            self._handle(message)

    def pump(self, seconds: float) -> None:
        end = time.time() + seconds
        while time.time() < end:
            try:
                self._handle(json.loads(self.ws.recv()))
            except websocket.WebSocketTimeoutException:
                pass

    def eval(self, expression: str):
        result = self.send("Runtime.evaluate", {"expression": expression, "returnByValue": True})
        return (result or {}).get("result", {}).get("value")

    def metrics(self, width: int, height: int, scale: float) -> None:
        self.send("Emulation.setDeviceMetricsOverride", {"width": width, "height": height, "deviceScaleFactor": scale, "mobile": False})

    def shot(self, url: str, wait: float = 1.5) -> Image.Image:
        """Capture d'écran nette (PNG) d'une page."""
        self.send("Page.navigate", {"url": url})
        self.pump(wait)
        data = self.send("Page.captureScreenshot", {"format": "png"})["data"]
        return Image.open(io.BytesIO(base64.b64decode(data))).convert("RGB")


class Browser:
    def __init__(self, width: int, height: int):
        self.profile = tempfile.mkdtemp(prefix="busbuddy-rec-")
        chrome = next((c for c in CHROME if os.path.exists(c)), None)
        if not chrome:
            raise SystemExit("Chrome introuvable")
        self.process = subprocess.Popen(
            [chrome, "--headless=new", "--hide-scrollbars", f"--remote-debugging-port={PORT}", f"--user-data-dir={self.profile}",
             f"--window-size={width},{height}", "--autoplay-policy=no-user-gesture-required", "--force-device-scale-factor=1", "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        target = None
        for _ in range(60):
            try:
                targets = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json"))
                target = next(t for t in targets if t["type"] == "page")
                break
            except Exception:
                time.sleep(0.5)
        if not target:
            self.close()
            raise SystemExit("impossible de se connecter à Chrome")
        self.cdp = Cdp(target["webSocketDebuggerUrl"])
        self.cdp.send("Page.enable")

    def close(self) -> None:
        self.process.terminate()


def record_demo(cdp: Cdp, url: str, width: int, height: int, scale: float, end_text: str, limit: float):
    """Joue la page et retourne les images (instant, JPEG) jusqu'à quelques secondes après le bandeau de fin."""
    cdp.frames.clear()
    cdp.metrics(width, height, scale)
    cdp.send("Page.navigate", {"url": url})
    cdp.pump(0.3)
    cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 88, "maxWidth": round(width * scale), "maxHeight": round(height * scale), "everyNthFrame": 1})
    started, end_seen = time.time(), None
    while time.time() - started < limit:
        cdp.pump(0.5)
        text = (cdp.eval("document.getElementById('democap')?.innerText || ''") or "").replace("\n✕", "").strip()
        if text == end_text and end_seen is None:
            end_seen = time.time()
        if end_seen and time.time() - end_seen > 2.5:
            break
    cdp.send("Page.stopScreencast")
    print(f"{len(cdp.frames)} images reçues en {time.time() - started:.0f} s ; fin de la démo {'vue' if end_seen else 'NON vue'}")
    if len(cdp.frames) < 10:
        raise SystemExit("trop peu d'images : enregistrement abandonné")
    return trim_blank(list(cdp.frames))


def trim_blank(frames):
    """Retire les premières images quand la page n'est pas encore affichée (fond uni)."""
    start = 0
    while start < len(frames) - 10:
        pixels = np.asarray(Image.open(io.BytesIO(frames[start][1])).convert("L").resize((48, 96)), dtype=np.float32)
        if pixels.std() > 12:  # un vrai écran de l'application : couleurs variées
            break
        start += 1
    if start:
        print(f"{start} image(s) vide(s) au début retirée(s)")
    return frames[start:]


class Writer:
    def __init__(self, out: Path, width: int, height: int):
        out.parent.mkdir(parents=True, exist_ok=True)
        self.container = av.open(str(out), "w")
        self.stream = self.container.add_stream("libx264", rate=FPS)
        self.stream.width, self.stream.height, self.stream.pix_fmt = width, height, "yuv420p"
        self.stream.options = {"crf": "20", "preset": "medium"}

    def add(self, rgb: np.ndarray) -> None:
        for packet in self.stream.encode(av.VideoFrame.from_ndarray(rgb, format="rgb24")):
            self.container.mux(packet)

    def close(self) -> None:
        for packet in self.stream.encode():
            self.container.mux(packet)
        self.container.close()


def frame_at(frames, index: int, cache: dict, size: tuple[int, int]) -> np.ndarray:
    if index not in cache:
        cache.clear()
        image = Image.open(io.BytesIO(frames[index][1])).convert("RGB")
        if image.size != size:
            image = image.resize(size, Image.LANCZOS)
        cache[index] = np.asarray(image)
    return cache[index]


def encode_plain(frames, size: tuple[int, int], out: Path) -> float:
    """Remet les images à cadence fixe : pour chaque instant, la dernière image reçue."""
    writer = Writer(out, *size)
    t0, t1 = frames[0][0], frames[-1][0]
    total, index, cache = int((t1 - t0) * FPS) + 1, 0, {}
    for n in range(total):
        while index + 1 < len(frames) and frames[index + 1][0] <= t0 + n / FPS:
            index += 1
        writer.add(frame_at(frames, index, cache, size))
    writer.close()
    return total / FPS


def key_region(base: np.ndarray, x0: int, x1: int):
    """Zone verte de la page « à vide » entre les colonnes x0 et x1 : (boîte, opacité 0..1 de la zone, y compris les bords)."""
    green = (base[:, :, 1] > 200) & (base[:, :, 0] < 60) & (base[:, :, 2] < 60)
    green[:, :x0] = False
    green[:, x1:] = False
    ys, xs = np.where(green)
    box = (max(xs.min() - 4, 0), max(ys.min() - 4, 0), xs.max() + 5, ys.max() + 5)
    return box


def encode_slide(frames, base_url: str, cdp: Cdp, out: Path, phone_size: tuple[int, int]) -> float:
    cdp.metrics(1920, 1080, 1)
    base = np.asarray(cdp.shot(f"{base_url}&compose=base"), dtype=np.float32)
    base_m = np.asarray(cdp.shot(f"{base_url}&compose=base&key=m"), dtype=np.float32)  # même page, zones magenta
    # un pixel = (1-a) x fond + a x couleur-clé : l'écart entre les deux prises donne a exactement, y compris sur les bords arrondis
    alpha = np.clip(np.abs(base - base_m).sum(axis=2) / 765.0, 0, 1)[:, :, None]
    photos = [np.asarray(cdp.shot(f"{base_url}&compose={i}"), dtype=np.float32) for i in range(5)]

    sx0, sy0, sx1, sy1 = key_region(base, 680, 1250)  # écran du téléphone
    px0, py0, px1, py1 = key_region(base, 0, 680)  # photo de l'équipe (inclinée)
    sbase, pbase = base[sy0:sy1, sx0:sx1], base[py0:py1, px0:px1]
    a_screen, a_photo = alpha[sy0:sy1, sx0:sx1], alpha[py0:py1, px0:px1]
    layers = [p[py0:py1, px0:px1] for p in photos]
    screen_size = (sx1 - sx0, sy1 - sy0)

    writer = Writer(out, 1920, 1080)
    t0, t1 = frames[0][0], frames[-1][0]
    total, index, cache = int((t1 - t0) * FPS) + 1, 0, {}
    for n in range(total):
        t = n / FPS
        while index + 1 < len(frames) and frames[index + 1][0] <= t0 + t:
            index += 1
        frame = base.copy()
        # téléphone
        phone = frame_at(frames, index, cache, screen_size).astype(np.float32)
        frame[sy0:sy1, sx0:sx1] = sbase + a_screen * (phone - KEY)
        # photo de l'équipe : fondu enchaîné au début de chaque période
        k, into = int(t // SLIDE_EVERY), t % SLIDE_EVERY
        cur = layers[k % len(layers)]
        if k > 0 and into < SLIDE_FADE:
            mix = into / SLIDE_FADE
            cur = layers[(k - 1) % len(layers)] * (1 - mix) + cur * mix
        frame[py0:py1, px0:px1] = pbase + a_photo * (cur - KEY)
        writer.add(np.clip(frame, 0, 255).astype(np.uint8))
    writer.close()
    return total / FPS


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("base", nargs="?", default="http://localhost:5000", help="adresse du site (local ou déployé)")
    parser.add_argument("--phone", action="store_true", help="enregistrer le téléphone seul (780x1600) au lieu de la diapo")
    parser.add_argument("--lang", default="en")
    parser.add_argument("--intro", help="langue d'introduction : la démo dit bonjour dans cette langue puis passe à --lang (ex. --lang fr --intro it)")
    parser.add_argument("--speed", default="1", help="vitesse de la démo (1 = normale)")
    parser.add_argument("--tour", default="pitch", choices=["pitch", "full"])
    parser.add_argument("--out", type=Path, help="fichier de sortie (.mp4)")
    parser.add_argument("--max", type=float, default=240, help="durée maximale d'enregistrement en secondes")
    args = parser.parse_args()

    base = args.base.rstrip("/")
    end_key = "demo.p.end" if args.tour == "pitch" else "demo.c.end"  # le bandeau de fin : on s'arrête juste après
    end_text = json.loads((ROOT / "static" / "i18n" / f"{args.lang}.json").read_text(encoding="utf-8"))[end_key]
    app_url = f"{base}/?demo={args.speed}&tour={args.tour}&lang={args.lang}&autostart=1" + (f"&intro={args.intro}" if args.intro else "")
    suffix = "" if args.lang == "en" else f"-{args.lang}"  # bus-buddy-demo-fr.mp4

    browser = Browser(1920, 1080)
    try:
        if args.phone:
            frames = record_demo(browser.cdp, app_url, 390, 800, 2, end_text, args.max)
            out = args.out or ROOT / "docs" / "video" / f"bus-buddy-demo{suffix}-phone.mp4"
            seconds = encode_plain(frames, (780, 1600), out)
        else:
            # téléphone de la diapo : 468x964 pixels (écran 390x803 agrandi 1,2 fois, comme dans present.css)
            frames = record_demo(browser.cdp, app_url, 390, 803, 1.2, end_text, args.max)
            out = args.out or ROOT / "docs" / "video" / f"bus-buddy-demo{suffix}.mp4"
            seconds = encode_slide(frames, f"{base}/present/?lang={args.lang}&rec=1", browser.cdp, out, (468, 964))
        print(f"ok {out} ({seconds:.1f} s, {out.stat().st_size // 1024} Ko)")
    finally:
        browser.close()


if __name__ == "__main__":
    main()
