#!/usr/bin/env python3
"""Freeze Slingshot's real-world numbers into data/snapshot.json and the generated bodies_data.py (dev tool, never run by the game).

Reads five public pages (or saved copies of them, see --dir) and keeps only the numbers the game uses:

  1. JPL Solar System Dynamics, "Astrodynamic Parameters"      https://ssd.jpl.nasa.gov/astro_par.html
       the Sun's GM, the astronomical unit, the GM of Mercury and Venus (JPL planetary ephemeris DE440)
  2. JPL, "Approximate Positions of the Planets", Table 1     https://ssd.jpl.nasa.gov/planets/approx_pos.html
       each planet's semi-major axis, and its mean longitude at J2000 and rate (the starting angles)
  3. JPL, "Planetary Physical Parameters"                    https://ssd.jpl.nasa.gov/planets/phys_par.html
       each planet's mean radius
  4. JPL, "Planetary Satellite Physical Parameters"          https://ssd.jpl.nasa.gov/sats/phys_par/
       the GM of Earth..Neptune and of each moon, and each moon's mean radius
  5. JPL, "Planetary Satellite Mean Elements"                https://ssd.jpl.nasa.gov/sats/elem/
       each moon's semi-major axis and period
  (cross-check only) NASA Planetary Fact Sheet               https://nssdc.gsfc.nasa.gov/planetary/factsheet/

Usage:  python3 tools/fetch_snapshot.py [--dir saved_pages_dir] [--read YYYY-MM-DD]
With --dir the five pages are read from files named astro_par.html, approx_pos.html, planets_phys_par.html, sats_phys_par.html,
sats_elem.html, factsheet.html in that directory; otherwise they are fetched. The read date is written into the snapshot (the game
shows it on the About page and the Sources page).
"""

import argparse
import html as htmllib
import json
import re
import sys
import urllib.request
from pathlib import Path

GAME = Path(__file__).resolve().parent.parent
URLS = {
    "astro_par": "https://ssd.jpl.nasa.gov/astro_par.html",
    "approx_pos": "https://ssd.jpl.nasa.gov/planets/approx_pos.html",
    "planets_phys_par": "https://ssd.jpl.nasa.gov/planets/phys_par.html",
    "sats_phys_par": "https://ssd.jpl.nasa.gov/sats/phys_par/",
    "sats_elem": "https://ssd.jpl.nasa.gov/sats/elem/",
    "factsheet": "https://nssdc.gsfc.nasa.gov/planetary/factsheet/",
}
PLANETS = ["Mercury", "Venus", "Earth", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune"]
MOONS = {"Earth": ["Moon"], "Mars": ["Phobos", "Deimos"], "Jupiter": ["Io", "Europa", "Ganymede", "Callisto"],
         "Saturn": ["Mimas", "Enceladus", "Tethys", "Dione", "Rhea", "Titan", "Iapetus"],
         "Uranus": ["Ariel", "Umbriel", "Titania", "Oberon", "Miranda"], "Neptune": ["Triton"]}


def load(name, directory):
    if directory:
        return (Path(directory) / (name + ".html")).read_text(encoding="utf-8", errors="replace")
    request = urllib.request.Request(URLS[name], headers={"User-Agent": "NoyvjGames-slingshot-snapshot/1"})
    with urllib.request.urlopen(request, timeout=30) as reply:
        return reply.read().decode("utf-8", errors="replace")


def plain(text):
    text = re.sub(r"<script.*?</script>", "", text, flags=re.S)
    text = htmllib.unescape(re.sub(r"<[^>]+>", "|", text))
    return re.sub(r"(\| ?)+", "|", re.sub(r"\s+", " ", text))


def number(token):
    return float(re.match(r"\s*([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)", token).group(1))


def parse_astro_par(page):
    text = plain(page)
    sun = re.search(r"heliocentric gravitational constant\|GM\|sun\|([\d.]+) x 10\|(\d+)\|m\|3\|s\|-2", text)
    gm_sun = float(sun.group(1)) * 10 ** int(sun.group(2)) / 1e9          # m^3/s^2 -> km^3/s^2
    au = float(re.search(r"astronomical unit\|au\|(\d+) m", text).group(1)) / 1000.0
    gm = {}
    for name in ("Mercury", "Venus"):
        gm[name] = float(re.search(r"\|" + name + r"\|([\d.]+)\|", text).group(1))
    return {"gm_sun": gm_sun, "au_km": au, "gm": gm}


def parse_approx_pos(page):
    text = plain(page)
    start = text.index("Keplerian elements and their rates, with respect to the mean ecliptic and equinox of J2000, valid for the time-interval 1800 AD")
    block = text[start:text.index("Table 2a", start)]
    out = {}
    names = ["Mercury", "Venus", "EM Bary", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune"]
    for i, name in enumerate(names):
        match = re.search(re.escape(name) + r" ((?:[-+]?[\d.]+ ){11}[-+]?[\d.]+)", block)
        vals = [float(v) for v in match.group(1).split()]
        # a e I L varpi Omega, then the six rates
        out["Earth" if name == "EM Bary" else name] = {"a_au": vals[0], "L0_deg": vals[3], "Ldot_deg_per_cy": vals[9]}
    return out


def parse_planet_radii(page):
    text = plain(page)
    block = text[text.index("Planet|Equatorial"):text.index("Dwarf|Planet")]
    out = {}
    for i, name in enumerate(PLANETS):
        end = block.index(PLANETS[i + 1]) if i + 1 < len(PLANETS) else len(block)
        seg = block[block.index("|" + name + "|"):end] if i else block[block.index("|" + name + "|"):end]
        tokens = [t.strip() for t in seg.split("|")][2:]
        values = [number(t) for t in tokens if re.match(r"^[-+]?\d", t)]
        out[name] = {"radius_km": values[1], "orbital_period_y": values[5]}
    return out


def parse_sats_phys(page):
    start = page.index('<table id="sat_phys_par"')
    rows = re.findall(r"<tr>(.*?)</tr>", page[start:page.index("</table>", start)], flags=re.S)
    moons = {}
    for row in rows[2:]:
        cells = [re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", "", c))).strip() for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, flags=re.S)]
        if len(cells) >= 5:
            try:
                moons[cells[1]] = {"gm": number(cells[3]), "radius_km": number(cells[4])}
            except AttributeError:            # a moon with no GM yet ("n/a"): not one the game uses
                pass
    text = plain(page)
    block = text[text.index("Planet and Pluto GM Values"):]
    planets = {}
    for name in ("Earth", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune"):
        planets[name] = number(re.search(r"\|" + name + r"\|([\d.]+)", block).group(1))
    return moons, planets


def parse_sats_elem(page):
    start = page.index("<table")
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", page[start:], flags=re.S)
    out = {}
    for row in rows:
        cells = [re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", "", c))).strip() for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, flags=re.S)]
        if len(cells) >= 14 and cells[3].isdigit():
            try:
                out[cells[2]] = {"a_km": number(cells[7]), "period_d": number(cells[13])}
            except (ValueError, IndexError, AttributeError):
                pass
    return out


def parse_factsheet(page):
    text = plain(page)
    updated = re.search(r"Last Updated: ([^|]+)", text).group(1).strip()
    return {"last_updated": updated}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir")
    ap.add_argument("--read", default="2026-10-12")
    args = ap.parse_args(argv)
    pages = {name: load(name, args.dir) for name in URLS}
    astro = parse_astro_par(pages["astro_par"])
    approx = parse_approx_pos(pages["approx_pos"])
    radii = parse_planet_radii(pages["planets_phys_par"])
    moon_phys, planet_gm = parse_sats_phys(pages["sats_phys_par"])
    elem = parse_sats_elem(pages["sats_elem"])
    fact = parse_factsheet(pages["factsheet"])
    snapshot = {"read": args.read, "gm_sun": astro["gm_sun"], "au_km": astro["au_km"], "factsheet_updated": fact["last_updated"], "planets": {}, "moons": {}}
    for name in PLANETS:
        gm = planet_gm.get(name, astro["gm"].get(name))
        snapshot["planets"][name] = {"gm": gm, "radius_km": radii[name]["radius_km"], "a_au": approx[name]["a_au"],
                                     "L0_deg": approx[name]["L0_deg"], "Ldot_deg_per_cy": approx[name]["Ldot_deg_per_cy"],
                                     "orbital_period_y": radii[name]["orbital_period_y"]}
    for planet, names in MOONS.items():
        for name in names:
            snapshot["moons"][name] = {"planet": planet, "gm": moon_phys[name]["gm"], "radius_km": moon_phys[name]["radius_km"],
                                       "a_km": elem[name]["a_km"], "period_d": elem[name]["period_d"]}
    (GAME / "data").mkdir(exist_ok=True)
    (GAME / "data" / "snapshot.json").write_text(json.dumps(snapshot, indent=1) + "\n", encoding="utf-8")
    lines = ['"""Slingshot -- the real numbers, GENERATED by tools/fetch_snapshot.py from data/snapshot.json (do not edit by hand)."""', "",
             "READ = %r" % snapshot["read"], "GM_SUN = %r        # km^3/s^2, JPL DE440" % snapshot["gm_sun"], "AU_KM = %r" % snapshot["au_km"],
             "FACTSHEET_UPDATED = %r" % snapshot["factsheet_updated"], "",
             "# name: (GM km^3/s^2, mean radius km, semi-major axis au, mean longitude at J2000 deg, deg per Julian century, sidereal period years)",
             "PLANETS = {"]
    for name in PLANETS:
        p = snapshot["planets"][name]
        lines.append("    %r: (%r, %r, %r, %r, %r, %r)," % (name.lower(), p["gm"], p["radius_km"], p["a_au"], p["L0_deg"], p["Ldot_deg_per_cy"], p["orbital_period_y"]))
    lines += ["}", "", "# name: (parent planet, GM km^3/s^2, mean radius km, semi-major axis km, period days)", "MOONS = {"]
    for name, m in snapshot["moons"].items():
        lines.append("    %r: (%r, %r, %r, %r, %r)," % (name.lower(), m["planet"].lower(), m["gm"], m["radius_km"], m["a_km"], m["period_d"]))
    lines += ["}", ""]
    (GAME / "bodies_data.py").write_text("\n".join(lines), encoding="utf-8")
    print("wrote data/snapshot.json and bodies_data.py (read %s; fact sheet updated %s)" % (snapshot["read"], fact["last_updated"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
