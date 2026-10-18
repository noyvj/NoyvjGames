#!/usr/bin/env python3
"""Freeze EIA's real capacity factors into data/capacity_factors.json (dev tool, never run by the game).

Source: U.S. Energy Information Administration, Electric Power Monthly
  Table 6.07.A  Capacity Factors for Utility Scale Generators Primarily Using Fossil Fuels
      https://www.eia.gov/electricity/monthly/epm_table_grapher.php?t=epmt_6_07_a
  Table 6.07.B  Capacity Factors for Utility Scale Generators Primarily Using Non-Fossil Fuels
      https://www.eia.gov/electricity/monthly/epm_table_grapher.php?t=epmt_6_07_b
These pages send no access-control-allow-origin header (checked 2026-10-19), so a browser cannot read them live; the frozen file IS the data
and the game must say "EIA Electric Power Monthly, data for <month>, read on <date>". The EIA open-data API needs a free key, so it is not used.

Only the ANNUAL rows are kept (one row per year, 2016 to the last full year). Each column: time-adjusted capacity in MW and capacity factor in %.
Usage: python3 tools/fetch_capacity_factors.py [--read YYYY-MM-DD]      (stdlib only; if EIA changes the column order the script stops instead of guessing)
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
PAGES = {
    "6.07.A": ("https://www.eia.gov/electricity/monthly/epm_table_grapher.php?t=epmt_6_07_a",
               ["Coal", "Natural gas: combined cycle", "Natural gas: gas turbine", "Natural gas: steam turbine", "Natural gas: internal combustion",
                "Petroleum: steam turbine", "Petroleum: gas turbine", "Petroleum: internal combustion"],
               "Coal|Natural Gas|Petroleum|Year/Month|Combined Cycle|Gas Turbine|Steam Turbine|Internal Combustion|Steam Turbine|Gas Turbine|Internal Combustion|"),
    "6.07.B": ("https://www.eia.gov/electricity/monthly/epm_table_grapher.php?t=epmt_6_07_b",
               ["Geothermal", "Hydroelectric", "Nuclear", "Other biomass", "Other fossil gas", "Solar: photovoltaic", "Solar: thermal", "Wind", "Wood"],
               "Geothermal|Hydroelectric|Nuclear|Other Biomass|Other Fossil Gas|Solar|Wind|Wood|Year/Month|Photovoltaic|Thermal|"),
}
UA = "NoyvjGames-snapshot/1 (https://noyvj.github.io/NoyvjGames/)"


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60) as reply:
        return reply.read().decode("utf-8", errors="replace")


def plain(page):
    page = re.sub(r"<script.*?</script>", "", page, flags=re.S)
    text = html.unescape(re.sub(r"<[^>]+>", "|", page))
    return re.sub(r"(\| ?)+", "|", re.sub(r"\s+", " ", text))


def parse(table, page):
    url, names, header = PAGES[table]
    text = plain(page)
    if header not in text:
        raise SystemExit("EIA changed the column layout of Table %s: check the header and fix PAGES" % table)
    release = re.search(r"Data for ([A-Za-z]+ \d{4})\|Release Date:\|([A-Za-z]+ \d+, \d{4})", text)
    start = text.index("Annual Data|")
    end = text.index("|Year ", start)
    tokens = [t.strip() for t in text[start + len("Annual Data|"):end].split("|") if t.strip()]
    series = {name: [] for name in names}
    i = 0
    while i < len(tokens):
        year = int(tokens[i])
        cells = tokens[i + 1:i + 1 + 2 * len(names)]
        i += 1 + 2 * len(names)
        for k, name in enumerate(names):
            mw, cf = cells[2 * k], cells[2 * k + 1]
            if not mw.replace(",", "").replace(".", "").isdigit() or not cf.endswith("%"):
                continue                  # a column EIA leaves blank for that year
            series[name].append({"year": year, "capacity_mw": float(mw.replace(",", "")), "capacity_factor_pct": float(cf.rstrip("%"))})
    return {"table": "Table " + table, "url": url, "data_for": release.group(1), "release_date": release.group(2),
            "technologies": [{"label": name, "annual": series[name]} for name in names]}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--read", default=datetime.date.today().isoformat())
    args = ap.parse_args(argv)
    tables = [parse(t, get(PAGES[t][0])) for t in ("6.07.A", "6.07.B")]
    out = {"topic": "capacity_factors", "read": args.read,
           "source": {"name": "Electric Power Monthly, Tables 6.07.A and 6.07.B: Capacity Factors for Utility Scale Generators",
                      "publisher": "U.S. Energy Information Administration (EIA)",
                      "url": "https://www.eia.gov/electricity/monthly/",
                      "licence": "U.S. government data, public domain; EIA asks that it is cited as the source"},
           "capacity_unit": "MW (time-adjusted capacity)", "capacity_factor_unit": "percent of nameplate output over the year",
           "tables": tables}
    (GAME / "data").mkdir(exist_ok=True)
    (GAME / "data" / "capacity_factors.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print("wrote data/capacity_factors.json: %d technologies, data for %s" % (sum(len(t["technologies"]) for t in tables), tables[1]["data_for"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
