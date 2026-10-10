"""Construit le site statique (GitHub Pages) dans _site/ :

    python tools/build_site.py https://massyle78.github.io/LeFoyer

L'application est 100 % statique ; seule la page /qr/ est générée ici (au lieu de Flask).
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import STATIC, load_lines, qr_page_html, qr_svg_bytes  # noqa: E402


def main() -> None:
    base = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000").rstrip("/")
    site = ROOT / "_site"
    shutil.rmtree(site, ignore_errors=True)
    shutil.copytree(STATIC, site / "static", ignore=shutil.ignore_patterns("index.html", "sw.js", "manifest.webmanifest"))
    for name in ("index.html", "sw.js", "manifest.webmanifest"):
        shutil.copy(STATIC / name, site / name)
    (site / ".nojekyll").write_text("", encoding="utf-8")

    items = []
    for line in load_lines():
        number = line["number"]
        url = f"{base}/?line={number}"
        (site / "qr").mkdir(exist_ok=True)
        (site / "qr" / f"{number}.svg").write_bytes(qr_svg_bytes(url))
        items.append((number, line["stops"][-1]["name"], url, f"{number}.svg"))
    (site / "qr" / "index.html").write_text(qr_page_html(items), encoding="utf-8")
    print(f"site construit dans {site} (QR -> {base})")


if __name__ == "__main__":
    main()
