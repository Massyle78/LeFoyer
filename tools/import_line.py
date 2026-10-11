"""Importe une ligne de bus avec pictogrammes (dossier ou .zip « ligne-XXX-pictogrammes ») dans l'application.

    python tools/import_line.py "../new graphic chart/ligne-701-pictogrammes-.zip" --default

Le paquet contient `stops.json` (arrêts, communes, couleurs, ordre des arrêts dans chaque sens) et `png/icons/*.png`.
Le script :
  - copie les pictogrammes dans static/img/stops/<ligne>/ ;
  - crée une entrée de ligne PAR SENS dans static/data/lines.json (un QR code par sens : /?line=701 et /?line=701-<sens>) ;
  - avec --default, place la ligne en tête de liste et la déclare « ligne par défaut » (champ "default").
Relancer le script remplace les entrées de cette ligne (il est donc sans danger).
"""
import argparse
import json
import shutil
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINES = ROOT / "static" / "data" / "lines.json"


def find_pack(path: Path) -> Path:
    """Retourne le dossier qui contient stops.json (en dézippant si besoin)."""
    if path.suffix == ".zip":
        target = Path(tempfile.mkdtemp(prefix="busbuddy-line-"))
        with zipfile.ZipFile(path) as archive:
            archive.extractall(target)
        path = target
    for candidate in [path, *path.rglob("stops.json")]:
        folder = candidate if candidate.is_dir() else candidate.parent
        if (folder / "stops.json").exists():
            return folder
    raise SystemExit(f"stops.json introuvable dans {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pack", type=Path, help="dossier ou .zip du paquet de pictogrammes")
    parser.add_argument("--default", action="store_true", help="en faire la ligne par défaut (en tête de liste)")
    args = parser.parse_args()

    pack = find_pack(args.pack)
    data = json.loads((pack / "stops.json").read_text(encoding="utf-8"))
    number = data["line"]
    colors = data.get("colors_by_commune", {})
    by_id = {stop["id"]: stop for stop in data["stops"]}

    # pictogrammes
    folder = ROOT / "static" / "img" / "stops" / number
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    for stop in data["stops"]:
        shutil.copyfile(pack / stop["files"]["icon_png"], folder / f"{stop['id']}.png")

    def stop_entry(stop_id: str) -> dict:
        stop = by_id[stop_id]
        entry = {
            "id": stop["id"],
            "name": stop["display_name"],
            "commune": stop["commune"],
            "picto": f"{number}/{stop['id']}.png",
        }
        color = colors.get(stop["commune"], {}).get("main")
        if color:
            entry["color"] = color
        return entry

    # une ligne par sens : le premier sens garde le numéro seul (/?line=701), l'autre prend un suffixe
    new_lines = []
    for index, (direction, stop_ids) in enumerate(data["directions"].items()):
        key = number if index == 0 else f"{number}-{direction.removeprefix('to_')}"
        new_lines.append(
            {
                "number": key,
                "label": number,
                "operator": data.get("operator"),
                "route": data.get("route"),
                "stops": [stop_entry(stop_id) for stop_id in stop_ids],
            }
        )

    document = json.loads(LINES.read_text(encoding="utf-8"))
    keys = {line["number"] for line in new_lines}
    others = [line for line in document["lines"] if line["number"] not in keys and line.get("label") != number]
    old_index = next((i for i, line in enumerate(document["lines"]) if line["number"] in keys), None)
    if args.default or old_index is None:
        document["lines"] = new_lines + others
    else:  # on garde la place actuelle de la ligne
        others[old_index:old_index] = new_lines
        document["lines"] = others
    if args.default:
        document["default"] = number
    document["_comment"] = (
        "Une ligne = un sens = un QR code dans le bus : /?line=701. Ligne 701 (MBC, Morges - Lausanne) : données réelles avec "
        "pictogrammes ; lignes 8 et 123 : données de DÉMONSTRATION fictives. Les noms d'arrêts sont des noms propres : "
        "ils ne sont pas traduits. 'label' = numéro affiché si plusieurs sens partagent le même numéro."
    )
    LINES.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = ", ".join("{} ({} arrêts)".format(line["number"], len(line["stops"])) for line in new_lines)
    print(f"ligne {number} importée : {summary}")


if __name__ == "__main__":
    main()
