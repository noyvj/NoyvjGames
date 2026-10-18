#!/usr/bin/env python3
"""Freeze Our World in Data's solar module price curve into data/solar_learning_curve.json (dev tool, never run by the game).

Source: Our World in Data, "Solar photovoltaic module prices vs. cumulative capacity" (IRENA 2025, Nemet 2009, Farmer and Lafond 2016).
  CSV      https://ourworldindata.org/grapher/solar-pv-prices-vs-cumulative-capacity.csv     (columns Entity, Code, Year, price, capacity)
  Metadata https://ourworldindata.org/grapher/solar-pv-prices-vs-cumulative-capacity.metadata.json
Both answer with access-control-allow-origin: * (checked 2026-10-19), so the game's page can read the CSV live; the frozen copy is the fallback.

Usage: python3 tools/fetch_solar_curve.py [--read YYYY-MM-DD]      (stdlib only; rows are written in year order)
"""
import argparse
import csv
import datetime
import io
import json
import sys
import urllib.request
from pathlib import Path

GAME = Path(__file__).resolve().parent.parent
BASE = "https://ourworldindata.org/grapher/solar-pv-prices-vs-cumulative-capacity"
UA = "NoyvjGames-snapshot/1 (https://noyvj.github.io/NoyvjGames/)"


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60) as reply:
        return reply.read().decode("utf-8")


def build(csv_text, meta, read):
    rows = []
    for rec in csv.DictReader(io.StringIO(csv_text)):
        if rec["Entity"] != "World" or not rec["Solar PV module cost"] or not rec["Cumulative installed solar PV capacity"]:
            continue                      # a year with only one of the two numbers (2025 has capacity but no price yet) is left out
        rows.append({"year": int(rec["Year"]), "price_usd_per_watt": float(rec["Solar PV module cost"]),
                     "cumulative_capacity_mw": float(rec["Cumulative installed solar PV capacity"])})
    rows.sort(key=lambda r: r["year"])
    cols = meta["columns"]
    price_col = next(c for c in cols if "price" in c.lower())
    cap_col = next(c for c in cols if "capacity" in c.lower())
    return {
        "topic": "solar_learning_curve",
        "read": read,
        "title": meta["chart"]["title"],
        "source": {"name": "Our World in Data, Solar photovoltaic module prices vs. cumulative capacity",
                   "publisher": "Our World in Data (data: IRENA 2025; Nemet 2009; Farmer and Lafond 2016)",
                   "url": "https://ourworldindata.org/grapher/solar-pv-prices-vs-cumulative-capacity",
                   "csv_url": BASE + ".csv", "metadata_url": BASE + ".metadata.json",
                   "citation": meta["chart"]["citation"], "source_last_updated": cols[price_col]["lastUpdated"],
                   "licence": "CC BY 4.0 (Our World in Data); credit Our World in Data and the data providers named in the citation"},
        "price_unit": cols[price_col]["unit"], "capacity_unit": cols[cap_col]["unit"],
        "price_note": meta["chart"]["note"],
        "rows": rows,
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--read", default=datetime.date.today().isoformat())
    args = ap.parse_args(argv)
    data = build(get(BASE + ".csv"), json.loads(get(BASE + ".metadata.json")), args.read)
    (GAME / "data").mkdir(exist_ok=True)
    (GAME / "data" / "solar_learning_curve.json").write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    print("wrote data/solar_learning_curve.json: %d rows (%d to %d), read %s" % (len(data["rows"]), data["rows"][0]["year"], data["rows"][-1]["year"], args.read))
    return 0


if __name__ == "__main__":
    sys.exit(main())
