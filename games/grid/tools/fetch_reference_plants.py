#!/usr/bin/env python3
"""Freeze EIA's table of 19 reference power plants into data/reference_plants.json (dev tool, never run by the game).

Source: Sargent & Lundy for the U.S. Energy Information Administration, "Capital Cost and Performance Characteristic Estimates for Utility Scale
Electric Power Generating Technologies" (AEO2025 edition, Final Rev A, December 6, 2023, released January 10, 2024), Table 1-2 "Cost & Performance
Summary Table" (and Table 1-1 for the plant descriptions).
  https://www.eia.gov/analysis/studies/powerplants/capitalcost/pdf/capital_cost_AEO2025.pdf        (6 MB PDF, no CORS header: not readable live)
  page: https://www.eia.gov/analysis/studies/powerplants/capitalcost/
The PDF is a plain-text PDF (no OCR, no third-party library): this script inflates the page streams with zlib and reads the text operators.
Only five columns of Table 1-2 are kept: net nominal capacity (printed under a kW header, but the values are MW), net nominal heat rate (Btu/kWh), overnight capital cost ($/kW), fixed O&M ($/kW-year),
variable O&M ($/MWh). The emission columns wrap across lines in the PDF and are left out.  Case 4 also has a start cost, case 19 a cost per kWh.

Usage: python3 tools/fetch_reference_plants.py [--read YYYY-MM-DD] [--pdf saved.pdf]      (stdlib only; stops if a row does not parse)
"""
import argparse
import datetime
import json
import re
import sys
import urllib.request
import zlib
from pathlib import Path

GAME = Path(__file__).resolve().parent.parent
URL = "https://www.eia.gov/analysis/studies/powerplants/capitalcost/pdf/capital_cost_AEO2025.pdf"
UA = "NoyvjGames-snapshot/1 (https://noyvj.github.io/NoyvjGames/)"
# case number, id, name and description as Table 1-1 prints them, and the grid plant type each one belongs to (the game's own link, not EIA's)
CASES = [
    (1, "usc-coal", "Ultra-Supercritical (USC) Coal without Carbon Capture - Greenfield", "1 x 735 MW Gross, 650 MW Net", "coal"),
    (2, "usc-coal-ccs", "USC Coal 95% Carbon Capture", "1 x 819 MW Gross, 650 MW Net", "coal"),
    (3, "aero-ct", "Aeroderivative Combustion Turbines (CTs) - Simple Cycle", "4 x 54 MW Gross Aeroderivative, 211 MW Net", "gas"),
    (4, "h-class-ct", "CTs - Simple Cycle", "1 x H-Class Simple Cycle, 419 MW Net", "gas"),
    (5, "cc-2x2x1", "Combined-Cycle (CC) 2x2x1", "2 x 1 H Class CC, 1227 MW Net", "gas"),
    (6, "cc-1x1x1", "CC 1x1x1, Single Shaft", "1 x 1 H Class CC, 627 MW Net", "gas"),
    (7, "cc-ccs", "CC 1x1x1, Single Shaft, with 95% Carbon Capture", "1 x 1 H Class CC, 543 MW Net", "gas"),
    (8, "biomass-ccs", "Biomass Plant with 95% Carbon Capture", "1 x Bubbling Fluidized Bed (BFB), 50 MW Net", None),
    (9, "ap1000", "Advanced Nuclear (Brownfield)", "2 x AP1000, 2156 MW Net", "nuclear"),
    (10, "smr", "Small Modular Reactor Nuclear Power Plant", "6 x 80-MW Small Modular Reactor, 480 MW Net", "nuclear"),
    (11, "geothermal", "Geothermal", "Binary Cycle, 50 MW Net", None),
    (12, "hydro", "Hydroelectric Power Plant", "New Stream Reach Development, 100 MW Net", "hydro"),
    (13, "onshore-wind", "Onshore Wind - Large Plant Footprint: Great Plains Region", "200 MW, 2.8-MW Wind Turbine Generator (WTG)", "wind"),
    (14, "wind-repower", "Onshore Wind - Repowering/Retrofit", "150 MW, 1.5-1.62 MW WTG", "wind"),
    (15, "offshore-wind", "Fixed-bottom Offshore Wind: Monopile Foundations", "900 MW, 15 MW WTG", "wind"),
    (16, "solar-pv", "Solar Photovoltaic (PV) with Single-Axis Tracking", "150 MW AC", "solar"),
    (17, "solar-ac-battery", "Solar PV with Single-Axis Tracking and AC-Coupled Battery Storage", "150 MW AC Solar, 50 MW / 200 MWh Storage", "solar"),
    (18, "solar-dc-battery", "Solar PV with Single-Axis Tracking and DC-Coupled Battery Storage", "150 MW AC Solar, 50 MW / 200 MWh Storage", "solar"),
    (19, "bess", "Battery Energy Storage System (BESS)", "Lithium Ion, 150 MW / 600 MWh", "battery"),
]


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=120) as reply:
        return reply.read()


def unescape(b):
    table = {b"n": b"\n", b"r": b"\r", b"t": b"\t"}
    return re.sub(rb"\\([0-7]{1,3}|.)", lambda m: bytes([int(m.group(1), 8)]) if m.group(1)[:1].isdigit() else table.get(m.group(1), m.group(1)), b)


def pdf_text(data):
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
        for tok in re.finditer(rb"\[((?:[^\]\\]|\\.)*)\]\s*TJ|\(((?:[^)\\]|\\.)*)\)\s*Tj|(T[Dd*m])", body):
            if tok.group(1) is not None:
                out.append(b"".join(unescape(p) for p in re.findall(rb"\(((?:[^)\\]|\\.)*)\)", tok.group(1))))
            elif tok.group(2) is not None:
                out.append(unescape(tok.group(2)))
            else:
                out.append(b" ")
        pages.append(b"".join(out).decode("cp1252", "replace"))
    return "\n".join(pages)


def num(s):
    return float(s.replace(",", "").replace("$", ""))


def parse(text):
    flat = re.sub(r"\s+", " ", text)
    start = flat.index("Table 1-2 — Cost & Performance Summary Table")
    block = flat[start:flat.index("BASIS", start)]
    block = block.replace("$1.24/ MWh, $23,100/ Start", "$1.24 START23100").replace("$1,744, ($436/kWh)", "$1,744 KWH436")
    pattern = re.compile(r"(\d[\d,]*) (N/A|\d[\d,]*) (\$[\d,]+)(?: KWH436)? (\$[\d,.]+) (\$[\d.]+)(?: START23100)?")
    rows = pattern.findall(block)
    if len(rows) != len(CASES):
        raise SystemExit("expected %d rows in Table 1-2, found %d: the PDF layout changed" % (len(CASES), len(rows)))
    plants = []
    for (case, pid, name, desc, plant_type), (kw, heat, capex, fixed, var) in zip(CASES, rows):
        entry = {"case": case, "id": pid, "name": name, "description": desc, "grid_plant_type": plant_type,
                 "net_capacity_mw": num(kw), "heat_rate_btu_per_kwh": None if heat == "N/A" else num(heat),
                 "capital_cost_usd_per_kw": num(capex), "fixed_om_usd_per_kw_year": num(fixed), "variable_om_usd_per_mwh": num(var)}
        if case == 4:
            entry["start_cost_usd_per_start"] = 23100.0
        if case == 19:
            entry["capital_cost_usd_per_kwh"] = 436.0
        plants.append(entry)
    return plants


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--read", default=datetime.date.today().isoformat())
    ap.add_argument("--pdf")
    args = ap.parse_args(argv)
    data = Path(args.pdf).read_bytes() if args.pdf else get(URL)
    text = pdf_text(data)
    for case, pid, name, desc, _ in CASES:                    # the names must really be in Table 1-1
        key = re.sub(r"\s+", " ", name.split(" - ")[0]).replace("-", "")[:18]
        if key.replace(" ", "") not in re.sub(r"[\s–-]+", "", text).replace("-", ""):
            raise SystemExit("case %d (%s) not found in the PDF text" % (case, name))
    out = {"topic": "reference_plants", "read": args.read,
           "source": {"name": "Capital Cost and Performance Characteristic Estimates for Utility Scale Electric Power Generating Technologies (AEO2025), Table 1-2",
                      "publisher": "Sargent & Lundy for the U.S. Energy Information Administration (EIA), Final Rev A, December 6, 2023; released January 10, 2024",
                      "url": URL, "page_url": "https://www.eia.gov/analysis/studies/powerplants/capitalcost/",
                      "licence": "U.S. government report, public domain; the authors (Sargent & Lundy) state the views are theirs, not EIA's"},
           "live": False, "live_note": "A 6 MB PDF with no CORS header: a browser cannot read it, the snapshot is the data.",
           "units": {"net_capacity_mw": "MW (the PDF header says kW, but every value equals the net MW in the plant description, e.g. 650 for 650 MW Net)", "heat_rate_btu_per_kwh": "Btu/kWh (higher heating value, null = not applicable)",
                     "capital_cost_usd_per_kw": "US$ per kW, overnight", "fixed_om_usd_per_kw_year": "US$ per kW-year", "variable_om_usd_per_mwh": "US$ per MWh"},
           "plants": parse(text)}
    (GAME / "data").mkdir(exist_ok=True)
    (GAME / "data" / "reference_plants.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print("wrote data/reference_plants.json: %d plants" % len(out["plants"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
