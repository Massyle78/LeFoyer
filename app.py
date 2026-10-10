"""Serveur de Bus Buddy (web app).

L'application tourne ENTIÈREMENT dans le navigateur du téléphone (aucune communication avec le
conducteur, rien n'est envoyé au serveur). Ce serveur Python sert seulement :
  - l'application (fichiers statiques) ;
  - les QR codes à coller dans les bus : /qr  (un par ligne -> /?line=8).

    python app.py                 puis ouvrir http://localhost:5000 ; /qr pour les QR codes
    python app.py --port 8080
    BUSBUDDY_PUBLIC_URL=https://busbuddy.example.org python app.py     (URL mise dans les QR codes)
"""
import argparse
import io
import json
import os
import socket
from html import escape
from pathlib import Path

import segno
from flask import Flask, Response, abort, request, send_from_directory

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"

app = Flask(__name__, static_folder=str(STATIC), static_url_path="/static")


def load_lines() -> list:
    return json.loads((STATIC / "data" / "lines.json").read_text(encoding="utf-8"))["lines"]


def lan_ip() -> str:
    """Adresse de l'ordinateur sur le réseau local (pour qu'un téléphone puisse scanner le QR)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))  # aucune donnée envoyée
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def public_base() -> str:
    configured = os.environ.get("BUSBUDDY_PUBLIC_URL")
    if configured:
        return configured.rstrip("/")
    name, _, port = request.host.partition(":")
    if name in ("localhost", "127.0.0.1"):
        name = lan_ip()
    return f"{request.scheme}://{name}{':' + port if port else ''}"


def line_url(number: str) -> str:
    return f"{public_base()}/?line={number}"


# --- application -----------------------------------------------------------------------------------
@app.get("/")
def index():
    return send_from_directory(STATIC, "index.html", max_age=0)


@app.get("/manifest.webmanifest")
def manifest():
    return send_from_directory(STATIC, "manifest.webmanifest", mimetype="application/manifest+json")


@app.get("/sw.js")
def service_worker():
    return send_from_directory(STATIC, "sw.js", mimetype="text/javascript", max_age=0)


@app.after_request
def no_stale_files(response):
    if request.path.startswith("/static/") and not request.path.startswith("/static/img") \
            and not request.path.startswith("/static/fonts"):
        response.headers["Cache-Control"] = "no-cache"
    return response


# --- QR codes ----------------------------------------------------------------------------------------
def qr_svg_bytes(url: str) -> bytes:
    out = io.BytesIO()
    segno.make(url, error="m").save(out, kind="svg", scale=10, border=2, dark="#1D05A9", light="#ffffff")
    return out.getvalue()


def qr_page_html(items) -> str:
    """items : (numéro, terminus, url à encoder, adresse de l'image SVG). Réutilisé par tools/build_site.py."""
    cards = []
    for number, terminus, url, src in items:
        cards.append(
            f"""<figure><img src="{escape(src)}" alt="QR code ligne {escape(number)}">
            <figcaption><b>{escape(number)}</b> → {escape(terminus)}<small>{escape(url)}</small></figcaption></figure>"""
        )
    return f"""<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Bus Buddy · QR codes</title>
<style>
body{{font-family:Helvetica,Arial,sans-serif;background:#FEDADA;margin:0;padding:24px;color:#0d0d12}}
h1{{color:#1D05A9;margin:0 0 4px}} p{{margin:0 0 20px}}
main{{display:flex;flex-wrap:wrap;gap:20px}}
figure{{margin:0;background:#fff;border-radius:24px;padding:18px;width:260px;text-align:center}}
figure img{{width:100%}} b{{background:#1D05A9;color:#fff;border-radius:10px;padding:2px 12px;font-size:28px}}
figcaption{{margin-top:8px;font-size:20px;text-transform:uppercase}} small{{display:block;text-transform:none;font-size:12px;color:#555;word-break:break-all;margin-top:6px}}
@media print{{body{{background:#fff}}}}
</style>
<h1>Bus Buddy</h1><p>Un QR code par bus : le passager le scanne, l'application s'ouvre sur la bonne ligne. Imprimez cette page.</p>
<main>{''.join(cards)}</main></html>"""


@app.get("/qr/<number>.svg")
def qr_svg(number: str):
    if number not in {line["number"] for line in load_lines()}:
        abort(404)
    return Response(qr_svg_bytes(line_url(number)), mimetype="image/svg+xml")


@app.get("/qr")
def qr_page():
    items = [(line["number"], line["stops"][-1]["name"], line_url(line["number"]), f"/qr/{line['number']}.svg")
             for line in load_lines()]
    return Response(qr_page_html(items), mimetype="text/html")


@app.get("/preview")
def preview():
    """Outil de développement : plusieurs écrans côte à côte en taille téléphone (390x800).
    /preview?q=lang%3Dfr%26line%3D8&q=...&scale=0.6"""
    scale = float(request.args.get("scale", "1"))
    height = int(request.args.get("h", "800"))
    frames = "".join(
        f'<div style="width:{390 * scale}px;height:{height * scale}px;overflow:hidden;border-radius:12px;flex:none">'
        f'<iframe src="/?{escape(q)}" style="border:0;width:390px;height:{height}px;transform:scale({scale});transform-origin:0 0"></iframe></div>'
        for q in request.args.getlist("q")
    )
    return Response(f'<body style="margin:8px;background:#777;display:flex;gap:8px">{frames}', mimetype="text/html")


def main() -> None:
    parser = argparse.ArgumentParser(description="Serveur Bus Buddy")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()
    print(f"\n  Bus Buddy\n  sur cet ordinateur : http://localhost:{args.port}/   (démo auto : /?demo=2)"
          f"\n  sur le téléphone   : http://{lan_ip()}:{args.port}/   (même Wi-Fi)"
          f"\n  QR codes à scanner : http://localhost:{args.port}/qr\n")
    app.run(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
