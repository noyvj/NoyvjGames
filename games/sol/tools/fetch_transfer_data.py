#!/usr/bin/env python3
"""Freeze the NASA/JPL numbers a transfer-window puzzle needs into data/transfer_data.json (dev tool, never run by the game).

Sources (all NASA Jet Propulsion Laboratory, Solar System Dynamics; none sends an access-control-allow-origin header, checked 2026-10-19, so a browser cannot
read them and the frozen file IS the data; the game must say "a dated snapshot of NASA/JPL numbers, read <date>"):
  1. Astrodynamic Parameters   https://ssd.jpl.nasa.gov/astro_par.html            the Sun's GM and the astronomical unit (JPL planetary ephemeris DE440)
  2. Approximate Positions of the Planets, Table 1   https://ssd.jpl.nasa.gov/planets/approx_pos.html     semi-major axis (au) of Venus, Earth (EM barycentre), Mars, Jupiter, Saturn
  3. Planetary Physical Parameters   https://ssd.jpl.nasa.gov/planets/phys_par.html     orbital period (years) of the same planets
  4. Small-Body Database API   https://ssd-api.jpl.nasa.gov/sbdb.api?sstr=<name>&full-prec=1     Ceres (the Asteroid Belt's largest body) and Pluto: a, e, period
  5. Planetary Satellite Mean Elements   https://ssd.jpl.nasa.gov/sats/elem/        the Moon's semi-major axis (km) and period (days)
Values are copied exactly as published; nothing is derived (transfer times and delta-v are the game's own arithmetic).

Usage: python3 tools/fetch_transfer_data.py [--read YYYY-MM-DD]      (stdlib only; stops if a number is not found)
"""
import argparse
import datetime
import html as htmllib
import json
import re
import sys
import urllib.request
from pathlib import Path

GAME = Path(__file__).resolve().parent.parent
UA = "NoyvjGames-snapshot/1 (https://noyvj.github.io/NoyvjGames/)"
URLS = {"astro_par": "https://ssd.jpl.nasa.gov/astro_par.html", "approx_pos": "https://ssd.jpl.nasa.gov/planets/approx_pos.html",
        "phys_par": "https://ssd.jpl.nasa.gov/planets/phys_par.html", "sats_elem": "https://ssd.jpl.nasa.gov/sats/elem/",
        "ceres": "https://ssd-api.jpl.nasa.gov/sbdb.api?sstr=Ceres&full-prec=1", "pluto": "https://ssd-api.jpl.nasa.gov/sbdb.api?sstr=Pluto&full-prec=1"}
PLANETS = ["Mercury", "Venus", "Earth", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune"]
WORLD_OF = {"Venus": "Venus", "Earth": "Earth", "Mars": "Mars", "Jupiter": "JupiterMoons", "Saturn": "SaturnMoons"}   # SOL's world keys


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60) as reply:
        return reply.read().decode("utf-8", errors="replace")


def plain(page):
    page = re.sub(r"<script.*?</script>", "", page, flags=re.S)
    text = htmllib.unescape(re.sub(r"<[^>]+>", "|", page))
    return re.sub(r"(\| ?)+", "|", re.sub(r"\s+", " ", text))


def number(token):
    return float(re.match(r"\s*([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)", token).group(1))


def parse_astro_par(page):
    text = plain(page)
    sun = re.search(r"heliocentric gravitational constant\|GM\|sun\|([\d.]+) x 10\|(\d+)\|m\|3\|s\|-2", text)
    au = re.search(r"astronomical unit\|au\|(\d+) m", text)
    return float(sun.group(1)) * 10 ** int(sun.group(2)) / 1e9, float(au.group(1)) / 1000.0


def parse_approx_pos(page):
    text = plain(page)
    start = text.index("Keplerian elements and their rates, with respect to the mean ecliptic and equinox of J2000, valid for the time-interval 1800 AD")
    block = text[start:text.index("Table 2a", start)]
    out = {}
    for name in ("Venus", "EM Bary", "Mars", "Jupiter", "Saturn"):
        vals = [float(v) for v in re.search(re.escape(name) + r" ((?:[-+]?[\d.]+ ){11}[-+]?[\d.]+)", block).group(1).split()]
        out["Earth" if name == "EM Bary" else name] = vals[0]
    return out


def parse_periods(page):
    text = plain(page)
    block = text[text.index("Planet|Equatorial"):text.index("Dwarf|Planet")]
    out = {}
    for i, name in enumerate(PLANETS):
        end = block.index(PLANETS[i + 1]) if i + 1 < len(PLANETS) else len(block)
        seg = block[block.index("|" + name + "|"):end]
        values = [number(t) for t in (t.strip() for t in seg.split("|")[2:]) if re.match(r"^[-+]?\d", t)]
        out[name] = values[5]
    return out


def parse_moon(page):
    start = page.index("<table")
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", page[start:], flags=re.S):
        cells = [re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", "", c))).strip() for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, flags=re.S)]
        if len(cells) >= 14 and cells[3].isdigit() and cells[2] == "Moon":
            return number(cells[7]), number(cells[13])
    raise SystemExit("the Moon row was not found on the satellite elements page")


def sbdb(text):
    data = json.loads(text)
    el = {e["name"]: e["value"] for e in data["orbit"]["elements"]}
    return {"full_name": data["object"]["fullname"], "a_au": float(el["a"]), "e": float(el["e"]), "period_days": float(el["per"]), "epoch_jd": data["orbit"]["epoch"], "sbdb_spkid": data["object"]["spkid"]}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--read", default=datetime.date.today().isoformat())
    args = ap.parse_args(argv)
    pages = {k: get(u) for k, u in URLS.items()}
    gm_sun, au_km = parse_astro_par(pages["astro_par"])
    a = parse_approx_pos(pages["approx_pos"])
    per = parse_periods(pages["phys_par"])
    moon_a, moon_p = parse_moon(pages["sats_elem"])
    bodies = []
    for planet, world in WORLD_OF.items():
        bodies.append({"world": world, "body": planet, "orbits": "Sun", "semi_major_axis_au": a[planet], "orbital_period_years": per[planet], "source": "approx_pos + phys_par"})
    for key, world in (("ceres", "AsteroidBelt"), ("pluto", "Pluto")):
        d = sbdb(pages[key])
        bodies.append({"world": world, "body": d["full_name"], "orbits": "Sun", "semi_major_axis_au": d["a_au"], "eccentricity": d["e"],
                       "orbital_period_days": d["period_days"], "source": "sbdb",
                       "orbit_epoch_jd": d["epoch_jd"]})
    bodies.append({"world": "Moon", "body": "Moon", "orbits": "Earth", "semi_major_axis_km": moon_a, "orbital_period_days": moon_p, "source": "sats_elem"})
    out = {"topic": "transfer_data", "read": args.read,
           "sources": [{"name": "Astrodynamic Parameters", "url": URLS["astro_par"]},
                       {"name": "Approximate Positions of the Planets (Table 1)", "url": URLS["approx_pos"]},
                       {"name": "Planetary Physical Parameters", "url": URLS["phys_par"]},
                       {"name": "Small-Body Database API (Ceres, Pluto), full precision", "url": "https://ssd-api.jpl.nasa.gov/doc/sbdb.html"},
                       {"name": "Planetary Satellite Mean Elements", "url": URLS["sats_elem"]}],
           "publisher": "NASA Jet Propulsion Laboratory, Solar System Dynamics group",
           "licence": "NASA content is generally not copyrighted (NASA media usage guidelines); credit NASA/JPL-Caltech",
           "live": False, "live_note": "No CORS header on any of the five: a browser cannot read them, the snapshot is the data.",
           "gm_sun_km3_s2": gm_sun, "astronomical_unit_km": au_km, "bodies": bodies}
    (GAME / "data").mkdir(exist_ok=True)
    (GAME / "data" / "transfer_data.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print("wrote data/transfer_data.json: %d bodies (GM sun %s, au %s km)" % (len(bodies), gm_sun, au_km))
    return 0


if __name__ == "__main__":
    sys.exit(main())
