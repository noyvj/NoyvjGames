#!/usr/bin/env python3
"""Freeze the IPCC AR6 global sea level table into data/sea_level_pathways.json (dev tool, never run by the game).

Source: IPCC Sixth Assessment Report, Working Group I, Chapter 9 "Ocean, Cryosphere and Sea Level Change" (Fox-Kemper et al. 2021),
Table 9.9 "Global mean sea level projections for five Shared Socio-economic Pathway (SSP) scenarios, relative to a baseline of 1995-2014, in metres".
  https://www.ipcc.ch/report/ar6/wg1/chapter/chapter-9/      (a 2 MB page; no access-control-allow-origin header, checked 2026-10-19:
  a browser cannot read it, so the frozen file IS the data and the game must call it a dated snapshot)
Every cell is a median with its "likely" range, e.g. 0.44 (0.32-0.62) m. Rates are mm per year. The sixth column is the SSP5-8.5 low-confidence case.

Usage: python3 tools/fetch_sea_level.py [--read YYYY-MM-DD] [--html saved.html]      (stdlib only; stops if the table is not found as expected)
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
URL = "https://www.ipcc.ch/report/ar6/wg1/chapter/chapter-9/"
UA = "NoyvjGames-snapshot/1 (https://noyvj.github.io/NoyvjGames/)"
SCENARIOS = ["SSP1-1.9", "SSP1-2.6", "SSP2-4.5", "SSP3-7.0", "SSP5-8.5", "SSP5-8.5 low confidence"]
ROWS = [("thermal_expansion_2100", "Thermal expansion", "m"), ("greenland_2100", "Greenland", "m"), ("antarctica_2100", "Antarctica", "m"),
        ("glaciers_2100", "Glaciers", "m"), ("land_water_storage_2100", "Land-water Storage", "m"),
        ("total_2030", "Total (2030)", "m"), ("total_2050", "Total (2050)", "m"), ("total_2090", "Total (2090)", "m"),
        ("total_2100", "Total (2100)", "m"), ("total_2150", "Total (2150)", "m"),
        ("rate_2040_2060", "Rate (2040–2060)", "mm per year"), ("rate_2080_2100", "Rate (2080–2100)", "mm per year")]
CELL = r"(\d+(?:\.\d+)?) \((\d+(?:\.\d+)?)–(\d+(?:\.\d+)?)\)"


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=120) as reply:
        return reply.read().decode("utf-8", errors="replace")


def plain(page):
    page = re.sub(r"<script.*?</script>", "", page, flags=re.S)
    text = html.unescape(re.sub(r"<[^>]+>", "|", page))
    return re.sub(r"(\| ?)+", "|", re.sub(r"\s+", " ", text))


def build(page, read):
    text = plain(page)
    start = text.index("SSP1-1.9|SSP1-2.6|SSP2-4.5|SSP3-7.0|SSP5-8.5|SSP5-8.5|Low Confidence|")
    block = text[start:text.index("|Beyond 2050, the scenarios", start)].replace("(204|0–", "(2040–")
    rows = {}
    for key, label, unit in ROWS:
        m = re.search(re.escape(label) + r" ?\|((?:" + CELL + r" ?\|?){6})", block)
        if not m:
            raise SystemExit("row not found in Table 9.9: " + label)
        cells = re.findall(CELL, m.group(1))
        rows[key] = {"unit": unit, "values": {s: {"median": float(c[0]), "likely_low": float(c[1]), "likely_high": float(c[2])}
                                               for s, c in zip(SCENARIOS, cells)}}
    return {"topic": "sea_level_pathways", "read": read,
            "source": {"name": "IPCC AR6 WGI Chapter 9, Table 9.9: Global mean sea level projections for five SSP scenarios, relative to 1995-2014",
                       "publisher": "Intergovernmental Panel on Climate Change (IPCC), Working Group I, Sixth Assessment Report (2021)",
                       "url": URL, "licence": "IPCC reports may be reproduced with credit for non-commercial use (IPCC copyright terms); only the numbers are kept here"},
            "live": False, "live_note": "No CORS header on the IPCC page: a browser cannot read it, the snapshot is the data.",
            "baseline": "1995-2014", "scenarios": SCENARIOS,
            "note": "Each value is a median with its likely range (assessed 17th-83rd percentile). The last scenario is SSP5-8.5 with low-confidence ice-sheet processes: its range is a p-box, not an assessed likely range.",
            "rows": rows}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--read", default=datetime.date.today().isoformat())
    ap.add_argument("--html")
    args = ap.parse_args(argv)
    page = Path(args.html).read_text(encoding="utf-8", errors="replace") if args.html else get(URL)
    data = build(page, args.read)
    (GAME / "data").mkdir(exist_ok=True)
    (GAME / "data" / "sea_level_pathways.json").write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    t = data["rows"]["total_2100"]["values"]
    print("wrote data/sea_level_pathways.json: %d rows x %d scenarios; total 2100 SSP1-2.6 %s, SSP5-8.5 %s" % (len(data["rows"]), len(SCENARIOS), t["SSP1-2.6"]["median"], t["SSP5-8.5"]["median"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
