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

    def test_page_de_presentation(self):
        redirect = self.client.get("/present?demo=2&lang=fr")
        self.assertEqual(redirect.status_code, 302)
        self.assertTrue(redirect.headers["Location"].endswith("/static/present.html?demo=2&lang=fr"))
        page = self.client.get("/static/present.html").data.decode()
        for needle in ("img/qr-701.svg", "js/present.js", "img/team/team-1.jpg", 'id="demo"'):
            self.assertIn(needle, page)
        for path in ("/static/js/present.js", "/static/css/present.css", "/static/img/team/team-1.jpg", "/static/img/team/team-5.jpg", "/static/img/qr-701.svg"):
            self.assertEqual(self.client.get(path).status_code, 200, path)

    def test_qr_de_la_presentation_est_celui_du_site_deploye(self):
        from app import qr_svg_bytes
        svg = self.client.get("/static/img/qr-701.svg").data.replace(b"\r\n", b"\n")
        self.assertEqual(svg, qr_svg_bytes("https://massyle78.github.io/LeFoyer/?line=701"))

    def test_qr_par_ligne(self):
        page = self.client.get("/qr").data.decode()
        for number in ("701", "701-tolochenaz", "8", "123"):
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
                for key in ("photo", "picto"):
                    if stop.get(key):
                        self.assertTrue((ROOT / "static/img/stops" / stop[key]).exists(), stop[key])

    def test_ligne_701_par_defaut(self):
        document = json.loads((ROOT / "static/data/lines.json").read_text(encoding="utf-8"))
        lines = document["lines"]
        self.assertEqual(document["default"], "701")
        self.assertEqual(lines[0]["number"], "701", "la ligne par défaut est en tête de liste")
        keys = [line["number"] for line in lines]
        self.assertEqual(len(keys), len(set(keys)), "clés de ligne uniques")
        by_key = {line["number"]: line for line in lines}
        self.assertEqual(by_key["701-tolochenaz"]["label"], "701")
        for key, terminus in (("701", "Bourdonnette"), ("701-tolochenaz", "La Plantaz")):
            stops = by_key[key]["stops"]
            self.assertEqual(len(stops), 24)
            self.assertEqual(len({stop["id"] for stop in stops}), 24, "arrêts uniques")
            self.assertEqual(stops[-1]["name"], terminus)
            self.assertTrue(all(stop.get("picto") for stop in stops), "un pictogramme par arrêt")
        ids = lambda key: {stop["id"] for stop in by_key[key]["stops"]}  # noqa: E731
        # à Morges, la boucle à sens unique ne dessert pas les mêmes arrêts dans les deux sens
        self.assertIn("morges-casino", ids("701"))
        self.assertNotIn("morges-casino", ids("701-tolochenaz"))
        self.assertIn("morges-st-louis", ids("701-tolochenaz"))


if __name__ == "__main__":
    unittest.main()

