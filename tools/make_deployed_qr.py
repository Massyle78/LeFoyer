"""Génère static/img/qr-701.svg : le QR code de la ligne 701 du site DÉPLOYÉ (utilisé par la page de présentation).

    python tools/make_deployed_qr.py                                         # https://massyle78.github.io/LeFoyer/?line=701
    python tools/make_deployed_qr.py "https://autre.site/?line=701"

Ce QR ne dépend pas du serveur qui sert la page : même en local, la diapositive et les vidéos montrent le QR du site déployé.
"""
import sys
from pathlib import Path

import segno

URL = "https://massyle78.github.io/LeFoyer/?line=701"
OUT = Path(__file__).resolve().parent.parent / "static" / "img" / "qr-701.svg"


def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else URL
    segno.make(url, error="m").save(str(OUT), kind="svg", scale=10, border=2, dark="#1D05A9", light="#ffffff")
    print(f"ok {OUT} -> {url}")


if __name__ == "__main__":
    main()
