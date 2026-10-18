#!/usr/bin/env python3
"""Freeze 41 Wonders (named sights) with a NASA-written fact each into data/wonders.json (dev tool, never run by the game).

Source: NASA Science (science.nasa.gov), read through its public WordPress REST API, no key:
  https://science.nasa.gov/wp-json/wp/v2/<kind>?slug=<slug>&_fields=id,slug,title,link,excerpt,modified,date     kind = topic (a NASA topic page) or posts (a Photojournal / news post)
The API answers with an access-control-allow-origin header naming the asking origin (checked 2026-10-19 with Origin https://noyvj.github.io), so the game's page can
read ONE sight's fact live by slug; the frozen file is the fallback. Search results (wp/v2/search) are NOT used by the game: they are only how the slugs below were found.
The fact is the page's own `excerpt` (NASA's summary sentence or two), copied exactly (HTML stripped, whitespace collapsed). Nothing is paraphrased here.
Some excerpts end with NASA's own "[...]" cut: `cut_short` is true for those and the game should show only the whole sentences before it.

Each sight: world (a SOL world key), name (the sight's name as the game shows it), kind and slug (where the fact lives), and the NASA page path that the slug must
resolve to (the script stops if NASA moved or re-used a slug).
Usage: python3 tools/fetch_wonders.py [--read YYYY-MM-DD]      (stdlib only; 1 request per sight, 1 second apart)
"""
import argparse
import datetime
import html
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

GAME = Path(__file__).resolve().parent.parent
UA = "NoyvjGames-snapshot/1 (https://noyvj.github.io/NoyvjGames/)"
API = "https://science.nasa.gov/wp-json/wp/v2/%s?slug=%s&_fields=id,slug,title,link,excerpt,modified,date"
# world, name, kind, slug, expected path under science.nasa.gov
SIGHTS = [
    ("Earth", "Mount Everest", "posts", "close-up-of-mount-everest-149632", "/earth/earth-observatory/close-up-of-mount-everest-149632/"),
    ("Earth", "Great Barrier Reef", "posts", "heat-stress-on-the-great-barrier-reef-152561", "/earth/earth-observatory/heat-stress-on-the-great-barrier-reef-152561/"),
    ("Earth", "The aurora", "topic", "auroras", None),
    ("Moon", "Tycho crater", "topic", "moon-tycho", "/3d-resources/moon-tycho/"),
    ("Moon", "Copernicus crater", "topic", "moon-copernicus-crater", "/3d-resources/moon-copernicus-crater/"),
    ("Moon", "South Pole-Aitken basin", "topic", "what-is-the-south-pole-aitken-basin", None),
    ("Moon", "Water ice at the poles", "topic", "moon-water-and-ices", None),
    ("Mars", "Olympus Mons", "posts", "olympus-mons", "/photojournal/olympus-mons/"),
    ("Mars", "Valles Marineris", "topic", "mars-valles-marineris", "/3d-resources/mars-valles-marineris/"),
    ("Mars", "Gale Crater", "topic", "mars-trek-inside-gale-crater", "/3d-resources/mars-trek-inside-gale-crater/"),
    ("Mars", "Hellas Planitia", "posts", "squiggles-in-hellas-planitia", "/photojournal/squiggles-in-hellas-planitia/"),
    ("Mars", "Tharsis", "topic", "mars-tharsis", "/3d-resources/mars-tharsis/"),
    ("Mars", "Arsia Mons", "posts", "arsia-mons-flank-3", "/photojournal/arsia-mons-flank-3/"),
    ("Mars", "The south polar cap", "posts", "pj-south-polar-layers-2-16", "/photojournal/pj-south-polar-layers-2-16/"),
    ("Mars", "Phobos", "topic", "phobos", "/mars/moons/phobos/"),
    ("Mars", "Deimos", "topic", "deimos", "/mars/moons/deimos/"),
    ("Venus", "Maxwell Montes", "posts", "venus-maxwell-montes-and-cleopatra-crater", "/photojournal/venus-maxwell-montes-and-cleopatra-crater/"),
    ("AsteroidBelt", "Ceres' bright spots", "posts", "map-of-ceres-bright-spots", "/photojournal/map-of-ceres-bright-spots/"),
    ("AsteroidBelt", "Occator Crater", "posts", "dawn-stereo-anaglyph-of-southeast-floor-and-rim-of-occator-crater-ceres",
     "/photojournal/dawn-stereo-anaglyph-of-southeast-floor-and-rim-of-occator-crater-ceres/"),
    ("AsteroidBelt", "Vesta", "topic", "4-vesta", "/solar-system/asteroids/4-vesta/"),
    ("AsteroidBelt", "Rheasilvia basin", "topic", "vesta-rheasilvia", None),
    ("AsteroidBelt", "Ida and Dactyl", "topic", "243-ida", None),
    ("AsteroidBelt", "Kleopatra", "topic", "asteroid-216-kleopatra", None),
    ("Pluto", "Tombaugh Regio", "posts", "plutos-bladed-terrain-in-3-d", None),
    ("Pluto", "Wright Mons", "posts", "wrights-stuff", None),
    ("Pluto", "Charon", "topic", "charon", "/dwarf-planets/pluto/moons/charon/"),
    ("Pluto", "Mordor Macula", "posts", "charon-in-enhanced-color", None),
    ("Pluto", "Serenity Chasma", "posts", "soaring-over-charon", None),
    ("Pluto", "Sputnik Planitia", "posts", "soaring-over-pluto", None),
    ("JupiterMoons", "The Great Red Spot", "posts", "nasas-hubble-watches-jupiters-great-red-spot-behave-like-a-stress-ball", None),
    ("JupiterMoons", "Loki Patera", "posts", "looking-into-ios-loki-patera-artists-concept", None),
    ("JupiterMoons", "Io's volcanic plumes", "posts", "junocam-captures-io-spouting-off", None),
    ("JupiterMoons", "Europa's ocean", "posts", "europas-mysterious-interior-artists-concept-3", None),
    ("JupiterMoons", "Ganymede", "topic", "ganymede", "/jupiter/jupiter-moons/ganymede/"),
    ("JupiterMoons", "Valhalla on Callisto", "posts", "the-valhalla-multi-ring-structure-on-callisto", None),
    ("SaturnMoons", "Titan's lakes", "posts", "titan-lakes", None),
    ("SaturnMoons", "Kraken Mare and Ligeia Mare", "posts", "titan-kraken-and-ligeia-in-sharper-focus", None),
    ("SaturnMoons", "Enceladus", "topic", "enceladus", None),
    ("SaturnMoons", "Enceladus' plume", "posts", "webb-maps-surprisingly-large-plume-jetting-from-saturns-moon-enceladus", None),
    ("SaturnMoons", "The ridge of Iapetus", "posts", "the-himalayas-of-iapetus", None),
    ("SaturnMoons", "Saturn's south polar decagon", "posts", "nasas-hubble-tracks-new-decagon-encircling-saturns-south-pole", None),
]


def get(kind, slug):
    time.sleep(1.0)
    req = urllib.request.Request(API % (kind, slug), headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as reply:
        return json.loads(reply.read().decode("utf-8"))


def clean(fragment):
    text = html.unescape(re.sub(r"<[^>]+>", " ", fragment))
    text = text.replace("Â ", " ").replace(" ", " ")
    return re.sub(r"\s+", " ", text).strip()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--read", default=datetime.date.today().isoformat())
    args = ap.parse_args(argv)
    out = []
    for world, name, kind, slug, path in SIGHTS:
        rows = get(kind, slug)
        if len(rows) != 1:
            raise SystemExit("slug %s/%s returned %d pages" % (kind, slug, len(rows)))
        row = rows[0]
        link = row["link"]
        if path and not link.endswith(path):
            raise SystemExit("slug %s now points at %s, expected %s" % (slug, link, path))
        fact = clean(row["excerpt"]["rendered"])
        if len(fact) < 40 or fact.startswith(("Image texture", "Eyes on", "Description")):
            raise SystemExit("no usable NASA excerpt for " + name)
        out.append({"world": world, "name": name, "fact": fact, "cut_short": fact.endswith("[\u2026]"), "nasa_title": clean(row["title"]["rendered"]), "url": link, "kind": kind, "slug": slug,
                    "page_modified": row["modified"], "page_date": row["date"],
                    "api": "https://science.nasa.gov/wp-json/wp/v2/%s?slug=%s&_fields=title,link,excerpt,modified" % (kind, slug)})
    data = {"topic": "wonders", "read": args.read,
            "source": {"name": "NASA Science (science.nasa.gov), page summaries via the WordPress REST API", "publisher": "National Aeronautics and Space Administration (NASA)",
                       "url": "https://science.nasa.gov/", "licence": "NASA content is generally not copyrighted (NASA media usage guidelines); credit NASA and the image credit shown on each page"},
            "live": True, "live_note": "CORS open. Live: fetch the sight's `api` URL, take [0].excerpt.rendered (strip tags) and [0].link. Fallback: this file's `fact`.",
            "wonders": out}
    (GAME / "data").mkdir(exist_ok=True)
    (GAME / "data" / "wonders.json").write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote data/wonders.json: %d sights in %d worlds" % (len(out), len({w['world'] for w in out})))
    return 0


if __name__ == "__main__":
    sys.exit(main())
