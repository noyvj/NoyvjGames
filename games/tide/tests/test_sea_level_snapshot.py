"""data/sea_level_pathways.json: the frozen IPCC AR6 Table 9.9 (tools/fetch_sea_level.py)."""
import json
import re
from pathlib import Path

DATA = json.loads((Path(__file__).resolve().parent.parent / "data" / "sea_level_pathways.json").read_text(encoding="utf-8"))
ROWS = DATA["rows"]


def test_source_and_date():
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", DATA["read"])
    for key in ("name", "publisher", "url", "licence"):
        assert DATA["source"][key]
    assert DATA["source"]["url"].startswith("https://www.ipcc.ch/") and DATA["live"] is False and DATA["baseline"] == "1995-2014"


def test_every_row_has_every_scenario_with_ordered_ranges():
    assert len(DATA["scenarios"]) == 6 and len(ROWS) == 12
    for key, row in ROWS.items():
        assert row["unit"] in ("m", "mm per year"), key
        assert list(row["values"]) == DATA["scenarios"], key
        for s, v in row["values"].items():
            assert v["likely_low"] <= v["median"] <= v["likely_high"], (key, s)
            assert v["likely_high"] < 40, (key, s)


def test_totals_rise_with_the_emissions_scenario_and_with_time():
    tot = lambda k: [ROWS[k]["values"][s]["median"] for s in DATA["scenarios"][:5]]
    assert tot("total_2100") == sorted(tot("total_2100"))
    for s in DATA["scenarios"]:
        series = [ROWS[k]["values"][s]["median"] for k in ("total_2030", "total_2050", "total_2090", "total_2100", "total_2150")]
        assert series == sorted(series), s


def test_headline_values_copied_from_table_9_9():
    t = ROWS["total_2100"]["values"]
    assert (t["SSP1-2.6"]["median"], t["SSP1-2.6"]["likely_low"], t["SSP1-2.6"]["likely_high"]) == (0.44, 0.32, 0.62)
    assert (t["SSP5-8.5"]["median"], t["SSP5-8.5"]["likely_low"], t["SSP5-8.5"]["likely_high"]) == (0.77, 0.63, 1.01)
    assert t["SSP5-8.5 low confidence"]["likely_high"] == 1.60
    # the components of SSP2-4.5 in 2100 add up to its total within rounding
    parts = sum(ROWS[k]["values"]["SSP2-4.5"]["median"] for k in ("thermal_expansion_2100", "greenland_2100", "antarctica_2100", "glaciers_2100", "land_water_storage_2100"))
    assert abs(parts - ROWS["total_2100"]["values"]["SSP2-4.5"]["median"]) < 0.03
