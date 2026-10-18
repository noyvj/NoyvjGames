#!/usr/bin/env python3
"""Freeze the per-hectare forest carbon figures into data/forest_carbon.json (dev tool, never run by the game).

Two sources:
  1. FAO, "Global Forest Resources Assessment 2020: Key findings" (PDF, 30 pages)   https://www.fao.org/3/ca8753en/ca8753en.pdf
     The global carbon stock and carbon density (tonnes of carbon per hectare, all forest carbon pools) for 1990 and 2020. No CORS header on this PDF
     (checked 2026-10-19): a browser cannot read it, so these numbers are a dated snapshot.
  2. Our World in Data, "Above-ground forest biomass" (FAO SDG indicator 15.2.1, tonnes per hectare, by country)   https://ourworldindata.org/grapher/above-ground-biomass-in-forest-per-hectare.csv
     CORS open (access-control-allow-origin: *), so the page can read the newest value for a country live; the file here is the fallback.
Nothing is converted here. Turning tonnes of carbon into tonnes of CO2 is the game's arithmetic (multiply by 44.01 / 12.011, the ratio of the molar masses of CO2 and carbon).
Biomass (not carbon) is what source 2 measures: do NOT show it as carbon.

Usage: python3 tools/fetch_forest_carbon.py [--read YYYY-MM-DD] [--pdf saved.pdf]      (stdlib only; stops if a sentence or number is not found)
"""
import argparse
import csv
import datetime
import io
import json
import re
import sys
import urllib.request
import zlib
from pathlib import Path

GAME = Path(__file__).resolve().parent.parent
UA = "NoyvjGames-snapshot/1 (https://noyvj.github.io/NoyvjGames/)"
PDF_URL = "https://www.fao.org/3/ca8753en/ca8753en.pdf"
OWID = "https://ourworldindata.org/grapher/above-ground-biomass-in-forest-per-hectare"
COUNTRIES = ["World", "Canada", "Russia", "Sweden", "Finland", "Norway", "United States", "Brazil", "Indonesia", "Democratic Republic of Congo", "Colombia", "Peru", "Malaysia"]


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=120) as reply:
        return reply.read()


def pdf_text(data):
    table = {b"n": b"\n", b"r": b"\r", b"t": b"\t"}

    def unesc(b):
        return re.sub(rb"\\([0-7]{1,3}|.)", lambda m: bytes([int(m.group(1), 8)]) if m.group(1)[:1].isdigit() else table.get(m.group(1), m.group(1)), b)

    pages = []
    for m in re.finditer(rb"stream\r?\n", data):
        start = m.end()
        try:
            body = zlib.decompress(data[start:data.find(b"endstream", start)])
        except zlib.error:
            continue
        if b"BT" not in body:
            continue
        out = []
        for tok in re.finditer(rb"\[((?:[^\]\\]|\\.)*)\]\s*TJ|\(((?:[^)\\]|\\.)*)\)\s*Tj|(T[Dd*m])|(\bET\b)", body):
            if tok.group(1) is not None:
                out.append(b"".join(unesc(p) for p in re.findall(rb"\(((?:[^)\\]|\\.)*)\)", tok.group(1))))
            elif tok.group(2) is not None:
                out.append(unesc(tok.group(2)))
            else:
                out.append(b" ")
        pages.append(b"".join(out).decode("cp1252", "replace"))
    return re.sub(r"\s+", " ", "\n".join(pages))


def fra(text):
    sentence = re.search(r"The total carbon stock in forests decreased from (\d+) gigatonnes in (\d{4}) to (\d+) gigatonnes in (\d{4}); carbon density increased slightly over the same period, from (\d+) tonnes to (\d+) tonnes per ha\.", text)
    share = re.search(r"Most forest carbon is found in the living biomass \((\d+) percent\) and soil organic matter \((\d+) percent\), with the remainder in dead wood and litter\.", text)
    area = re.search(r"The world has a total forest area of ([\d.]+) billion hectares \(ha\), which is (\d+) percent of the total land area\.", text)
    biomass = re.search(r"The world.s forests contain about (\d+) gigatonnes of living biomass \(above- and below-ground\) and (\d+) gigatonnes of dead wood\.", text)
    if not (sentence and share and area and biomass):
        raise SystemExit("a sentence was not found in the FAO Key findings text: the wording changed, check by hand")
    return {"carbon_stock_gt": {sentence.group(2): float(sentence.group(1)), sentence.group(4): float(sentence.group(3))},
            "carbon_density_t_per_ha": {sentence.group(2): float(sentence.group(5)), sentence.group(4): float(sentence.group(6))},
            "share_of_forest_carbon_in_living_biomass_percent": float(share.group(1)), "share_in_soil_organic_matter_percent": float(share.group(2)),
            "forest_area_billion_ha": float(area.group(1)), "forest_share_of_land_percent": float(area.group(2)),
            "living_biomass_gt": float(biomass.group(1)), "dead_wood_gt": float(biomass.group(2)),
            "exact_sentences": [sentence.group(0), share.group(0), area.group(0), biomass.group(0)]}


def owid():
    rows = list(csv.DictReader(io.StringIO(get(OWID + ".csv").decode("utf-8"))))
    meta = json.loads(get(OWID + ".metadata.json").decode("utf-8"))
    col = next(iter(meta["columns"]))
    latest = {}
    for r in rows:
        if r["Entity"] in COUNTRIES:
            value = r[next(k for k in r if k.startswith("Above-ground"))]
            if value != "":
                year = int(r["Year"])
                if r["Entity"] not in latest or year > latest[r["Entity"]]["year"]:
                    latest[r["Entity"]] = {"year": year, "above_ground_biomass_t_per_ha": float(value)}
    if set(latest) != set(COUNTRIES):
        raise SystemExit("OWID is missing: " + ", ".join(sorted(set(COUNTRIES) - set(latest))))
    c = meta["columns"][col]
    return {"series": col, "unit": c["unit"], "timespan": c["timespan"], "source_last_updated": c["lastUpdated"], "citation": meta["chart"]["citation"],
            "csv_url": OWID + ".csv", "chart_url": OWID, "latest": {k: latest[k] for k in COUNTRIES}}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--read", default=datetime.date.today().isoformat())
    ap.add_argument("--pdf")
    args = ap.parse_args(argv)
    pdf = Path(args.pdf).read_bytes() if args.pdf else get(PDF_URL)
    out = {"topic": "forest_carbon", "read": args.read,
           "fao_fra2020": dict(fra(pdf_text(pdf)), name="Global Forest Resources Assessment 2020: Key findings", publisher="Food and Agriculture Organization of the United Nations (FAO)",
                               url=PDF_URL, licence="FAO publication. No licence line was found in the PDF text, so only the numbers and four short sentences are kept, credited to FAO; check FAO's terms before copying more text", live=False),
           "owid_above_ground_biomass": dict(owid(), publisher="Our World in Data, data from FAO (SDG indicator 15.2.1)", licence="CC BY 4.0 (Our World in Data); credit OWID and FAO", live=True),
           "co2_per_carbon": {"formula": "tonnes CO2 = tonnes of carbon x 44.01 / 12.011", "note": "ratio of the molar masses of carbon dioxide and carbon: the game's own arithmetic, not a measured figure"}}
    (GAME / "data").mkdir(exist_ok=True)
    (GAME / "data" / "forest_carbon.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    d = out["fao_fra2020"]["carbon_density_t_per_ha"]
    print("wrote data/forest_carbon.json: FAO carbon density %s t/ha; %d OWID country values" % (d, len(out["owid_above_ground_biomass"]["latest"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
