"""Tests du serveur : python -m unittest discover -s tests -p "test_*.py" """
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import app  # noqa: E402


class ServerTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_index_et_fichiers_racine(self):
        self.assertIn(b"Bus Buddy", self.client.get("/").data)
        self.assertEqual(self.client.get("/sw.js").status_code, 200)
        manifest = self.client.get("/manifest.webmanifest")
        self.assertEqual(manifest.status_code, 200)
        self.assertEqual(json.loads(manifest.data)["display"], "standalone")

    def test_qr_par_ligne(self):
        page = self.client.get("/qr").data.decode()
        for number in ("8", "123"):
            self.assertIn(f"/qr/{number}.svg", page)
            svg = self.client.get(f"/qr/{number}.svg")
            self.assertEqual(svg.status_code, 200)
            self.assertEqual(svg.mimetype, "image/svg+xml")
        self.assertEqual(self.client.get("/qr/999.svg").status_code, 404)

    def test_qr_contient_lien_vers_la_ligne(self):
        page = self.client.get("/qr", base_url="https://busbuddy.example.org").data.decode()
        self.assertIn("https://busbuddy.example.org/?line=8", page)

    def test_donnees_et_langues_servies(self):
        for path in ("/static/data/lines.json", "/static/i18n/fr.json", "/static/i18n/en.json",
                     "/static/js/main.js", "/static/css/app.css"):
            self.assertEqual(self.client.get(path).status_code, 200, path)

    def test_langues_completes(self):
        base = json.loads((ROOT / "static/i18n/en.json").read_text(encoding="utf-8"))
        for code in ("fr", "de", "it"):
            other = json.loads((ROOT / f"static/i18n/{code}.json").read_text(encoding="utf-8"))
            self.assertEqual(sorted(set(base) - set(other)), [], f"clés manquantes en {code}")

    def test_icones_et_photos_existent(self):
        lines = json.loads((ROOT / "static/data/lines.json").read_text(encoding="utf-8"))["lines"]
        for line in lines:
            for stop in line["stops"]:
                if stop.get("photo"):
                    self.assertTrue((ROOT / "static/img/stops" / stop["photo"]).exists(), stop["photo"])


if __name__ == "__main__":
    unittest.main()
