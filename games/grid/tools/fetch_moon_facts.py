#!/usr/bin/env python3
"""Freeze the NASA Moon Fact Sheet numbers a Moon-base scenario needs into data/moon_facts.json (dev tool, never run by the game).

Source: NASA Space Science Data Coordinated Archive (NSSDCA), Moon Fact Sheet   https://nssdc.gsfc.nasa.gov/planetary/factsheet/moonfact.html
The page sends no access-control-allow-origin header (checked 2026-10-19), so a browser cannot read it live: the frozen file IS the data and
the game must call it "a dated snapshot of NASA's Moon Fact Sheet (page last updated <date>), read on <read date>".
Values are copied exactly as the page prints them; nothing is derived here (the length of the lunar night is the game's own arithmetic, not NASA's).

Usage: python3 tools/fetch_moon_facts.py [--read YYYY-MM-DD]     (stdlib only; stops if a label is missing instead of guessing)
"""
import argparse
import datetime
import html
import json
import re
import sys
import urllib.request
from pathlib import Path

GAME = Path(__file__).resolve().parent.parent
URL = "https://nssdc.gsfc.nasa.gov/planetary/factsheet/moonfact.html"
UA = "NoyvjGames-snapshot/1 (https://noyvj.github.io/NoyvjGames/)"
# key, label as printed on the page, unit, kind (number from the Moon column, or the page's own text)
ROWS = [
    ("surface_gravity", "Surface gravity (m/s|2|)", "m/s^2", "number"),
    ("escape_velocity", "Escape velocity (km/s)", "km/s", "number"),
    ("volumetric_mean_radius", "Volumetric mean radius (km)", "km", "number"),
    ("mean_density", "Mean density (kg/m|3|)", "kg/m^3", "number"),
    ("solar_irradiance", "Solar irradiance (W/m|2|)", "W/m^2", "number"),
    ("black_body_temperature", "Black-body temperature (K)", "K", "number"),
    ("revolution_period", "Revolution period (days)", "days", "number"),
    ("synodic_period", "Synodic period (days)", "days", "number"),
    ("sidereal_rotation_period", "Sidereal rotation period (hrs)", "hours", "number"),
    ("obliquity_to_orbit", "Obliquity to orbit (deg)", "degrees", "number"),
]


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60) as reply:
        return reply.read().decode("utf-8", errors="replace")


def plain(page):
    page = re.sub(r"<script.*?</script>", "", page, flags=re.S)
    text = html.unescape(re.sub(r"<[^>]+>", "|", page))
    return re.sub(r"(\| ?)+", "|", re.sub(r"\s+", " ", text))


def build(page, read):
    text = plain(page)
    facts = []
    for key, label, unit, _ in ROWS:
        m = re.search(re.escape(label) + r"\|([-\d.]+)\|", text)
        if not m:
            raise SystemExit("label not found on the Moon Fact Sheet: " + label)
        facts.append({"key": key, "label": label.replace("|", ""), "value": float(m.group(1)), "printed": m.group(1), "unit": unit})
    temp = re.search(r"Diurnal temperature range \(equator\): (\d+) K to (\d+) K", text)
    updated = re.search(r"Last Updated: ([^|]+)", text).group(1).strip()
    facts.append({"key": "diurnal_temperature_min", "label": "Diurnal temperature range (equator), coldest", "value": float(temp.group(1)), "printed": temp.group(1), "unit": "K"})
    facts.append({"key": "diurnal_temperature_max", "label": "Diurnal temperature range (equator), hottest", "value": float(temp.group(2)), "printed": temp.group(2), "unit": "K"})
    return {"topic": "moon_facts", "read": read, "page_last_updated": updated,
            "source": {"name": "Moon Fact Sheet", "publisher": "NASA Space Science Data Coordinated Archive (NSSDCA), Goddard Space Flight Center",
                       "url": URL, "licence": "NASA content is generally not copyrighted (NASA media usage guidelines); credit NASA"},
            "live": False, "live_note": "No CORS header on the page: a browser cannot read it, the snapshot is the data.",
            "facts": facts}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--read", default=datetime.date.today().isoformat())
    args = ap.parse_args(argv)
    data = build(get(URL), args.read)
    (GAME / "data").mkdir(exist_ok=True)
    (GAME / "data" / "moon_facts.json").write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    print("wrote data/moon_facts.json: %d facts (page last updated %s)" % (len(data["facts"]), data["page_last_updated"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
