#!/usr/bin/env python3
"""Read the two public sources and freeze what the charts need into data/snapshot.json (the dated offline copy).

  stars   the HYG star database v4.1 (github.com/astronexus/HYG-Database): position, magnitude, names
  figures the Stellarium "modern" sky culture (stellarium.org), which carries the IAU constellation line figures as Hipparcos id chains

Usage: python3 tools/fetch_snapshot.py [--hyg path/to/hygdata_v41.csv] [--stellarium path/to/index.json]
Without arguments both files are downloaded. Only the constellations named in chart_specs.py are kept. Run by hand, never from the game.
"""

import csv
import datetime
import json
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import chart_specs  # noqa: E402

HYG_URL = "https://raw.githubusercontent.com/astronexus/HYG-Database/main/hyg/CURRENT/hygdata_v41.csv"
STEL_URL = "https://raw.githubusercontent.com/Stellarium/stellarium/master/skycultures/modern/index.json"


def text_of(path, url):
    if path:
        return Path(path).read_text(encoding="utf-8")
    with urllib.request.urlopen(url, timeout=120) as response:
        return response.read().decode("utf-8")


def main(argv):
    args = dict(zip(argv[::2], argv[1::2]))
    stel = json.loads(text_of(args.get("--stellarium"), STEL_URL))
    wanted = {c["code"] for season in chart_specs.SEASONS for c in season["charts"]}
    lines, hips = {}, set()
    for con in stel["constellations"]:
        code = con["id"].split()[-1]
        if code in wanted:
            lines[code] = con["lines"]
            hips.update(h for chain in con["lines"] for h in chain)
    stars = {}
    reader = csv.DictReader(text_of(args.get("--hyg"), HYG_URL).splitlines())
    for row in reader:
        if row["hip"] and int(row["hip"]) in hips:
            stars[row["hip"]] = {k: row[k] for k in ("proper", "bayer", "flam", "con", "ra", "dec", "mag", "spect")}
    missing = hips - {int(h) for h in stars}
    if missing:
        raise SystemExit("stars missing from the star database: %s" % sorted(missing))
    out = {
        "read": chart_specs.READ_DATE if "--hyg" in args else datetime.date.today().isoformat(),
        "sources": {"stars": {"title": "HYG star database v4.1", "url": "https://github.com/astronexus/HYG-Database"},
                    "figures": {"title": "Stellarium modern sky culture (IAU constellation figures)", "url": "https://stellarium.org"}},
        "lines": lines, "stars": stars,
    }
    target = HERE.parent / "data" / "snapshot.json"
    target.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print("wrote %s: %d constellations, %d stars" % (target, len(lines), len(stars)))


if __name__ == "__main__":
    main(sys.argv[1:])
