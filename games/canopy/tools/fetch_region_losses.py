#!/usr/bin/env python3
"""Freeze the main causes of tree cover loss for a boreal and a tropical region into data/region_losses.json (dev tool, never run by the game).

Source: Our World in Data, "Tree cover loss by dominant driver" (data: Global Forest Watch / University of Maryland, Sims et al. 2025)
  CSV       https://ourworldindata.org/grapher/tree-cover-loss-by-dominant-driver.csv?country=<name>      (yearly hectares per driver, 2001 to the last year)
  Metadata  https://ourworldindata.org/grapher/tree-cover-loss-by-dominant-driver.metadata.json
CORS open (access-control-allow-origin: *, checked 2026-10-19): the page can read it live; this file is the fallback.

Regions: "boreal" = Canada and Russia (the two largest boreal countries by FAO's Global Forest Resources Assessment 2020), "tropical" = Brazil, Indonesia and
Democratic Republic of Congo (three of the largest tropical rainforest countries). Whole-country figures, so they include non-boreal and non-rainforest parts:
the game must say "tree cover loss in Canada and Russia", not "in the boreal forest".
"ten_year_total_ha" and "largest_driver" are COMPUTED here by adding the source's yearly values for the last ten years (nothing else is derived).

Usage: python3 tools/fetch_region_losses.py [--read YYYY-MM-DD]      (stdlib only; values are hectares exactly as the CSV prints them)
"""
import argparse
import csv
import datetime
import io
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

GAME = Path(__file__).resolve().parent.parent
UA = "NoyvjGames-snapshot/1 (https://noyvj.github.io/NoyvjGames/)"
BASE = "https://ourworldindata.org/grapher/tree-cover-loss-by-dominant-driver"
REGIONS = {"boreal": ["Canada", "Russia"], "tropical": ["Brazil", "Indonesia", "Democratic Republic of Congo"]}
DRIVERS = ["Settlements and infrastructure", "Mining and energy industry", "Other natural disturbances", "Shifting cultivation", "Logging", "Permanent agriculture", "Wildfire"]
LAST_TEN = 10


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=120) as reply:
        return reply.read().decode("utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--read", default=datetime.date.today().isoformat())
    args = ap.parse_args(argv)
    rows = list(csv.DictReader(io.StringIO(get(BASE + ".csv"))))
    if [k for k in rows[0] if k not in ("Entity", "Code", "Year")] != DRIVERS:
        raise SystemExit("OWID changed the driver columns: " + str(list(rows[0])))
    meta = json.loads(get(BASE + ".metadata.json"))
    descriptions = {v["titleShort"] if "titleShort" in v else k: (v.get("descriptionShort") or "") for k, v in meta["columns"].items()}
    countries = {}
    for name in sum(REGIONS.values(), []):
        series = [r for r in rows if r["Entity"] == name]
        if not series:
            raise SystemExit("no rows for " + name)
        years = {}
        for r in sorted(series, key=lambda r: int(r["Year"])):
            years[r["Year"]] = {d: (float(r[d]) if r[d] != "" else None) for d in DRIVERS}
        last = sorted(years)[-LAST_TEN:]
        total = {d: round(sum(years[y][d] or 0.0 for y in last), 3) for d in DRIVERS}
        countries[name] = {"years": years, "ten_year_window": [last[0], last[-1]], "ten_year_total_ha": total, "largest_driver": max(DRIVERS, key=lambda d: total[d])}
    out = {"topic": "region_losses", "read": args.read,
           "source": {"name": "Tree cover loss by dominant driver", "publisher": "Our World in Data; data from Global Forest Watch (World Resources Institute / University of Maryland)",
                      "url": BASE, "csv_url": BASE + ".csv", "metadata_url": BASE + ".metadata.json", "citation": meta["chart"]["citation"],
                      "licence": "CC BY 4.0 (Our World in Data); credit OWID and Global Forest Watch"},
           "unit": "hectares of tree cover lost per year", "note": meta["chart"]["subtitle"], "driver_meaning": descriptions,
           "regions": REGIONS, "drivers": DRIVERS, "live": True,
           "live_note": "CORS open. Live: GET csv_url?country=<name> and add the last ten years; fall back to this file.",
           "countries": countries}
    (GAME / "data").mkdir(exist_ok=True)
    (GAME / "data" / "region_losses.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote data/region_losses.json: " + "; ".join("%s -> %s" % (n, c["largest_driver"]) for n, c in countries.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
