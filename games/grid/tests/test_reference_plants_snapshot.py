"""data/reference_plants.json: the frozen EIA/Sargent & Lundy reference plant table (tools/fetch_reference_plants.py)."""
import json
import re
from pathlib import Path

DATA = json.loads((Path(__file__).resolve().parent.parent / "data" / "reference_plants.json").read_text(encoding="utf-8"))
PLANTS = DATA["plants"]
FIELDS = ("net_capacity_mw", "capital_cost_usd_per_kw", "fixed_om_usd_per_kw_year", "variable_om_usd_per_mwh")


def test_source_and_date():
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", DATA["read"])
    for key in ("name", "publisher", "url", "page_url", "licence"):
        assert DATA["source"][key]
    assert DATA["source"]["url"].startswith("https://www.eia.gov/")
    assert DATA["live"] is False and set(DATA["units"]) >= set(FIELDS)


def test_nineteen_plants_numbered_one_to_nineteen_with_unique_ids():
    assert [p["case"] for p in PLANTS] == list(range(1, 20))
    assert len({p["id"] for p in PLANTS}) == 19
    for p in PLANTS:
        assert p["name"] and p["description"]


def test_capacity_matches_the_net_mw_in_the_description():
    for p in PLANTS:
        m = re.search(r"(\d+) MW Net", p["description"].replace(",", ""))
        if m:
            assert float(m.group(1)) == p["net_capacity_mw"], p["id"]


def test_numbers_are_sane():
    for p in PLANTS:
        for f in FIELDS:
            assert p[f] >= 0, (p["id"], f)
        assert 50 <= p["net_capacity_mw"] <= 2200, p["id"]
        assert 800 < p["capital_cost_usd_per_kw"] < 13000, p["id"]
        if p["heat_rate_btu_per_kwh"] is not None:
            assert 6000 < p["heat_rate_btu_per_kwh"] < 20000, p["id"]


def test_spot_values_copied_from_table_1_2():
    by = {p["id"]: p for p in PLANTS}
    assert by["ap1000"]["capital_cost_usd_per_kw"] == 7861 and by["ap1000"]["net_capacity_mw"] == 2156
    assert by["cc-2x2x1"]["heat_rate_btu_per_kwh"] == 6266
    assert by["solar-pv"]["capital_cost_usd_per_kw"] == 1502
    assert by["bess"]["capital_cost_usd_per_kwh"] == 436.0
    assert by["h-class-ct"]["start_cost_usd_per_start"] == 23100.0


def test_grid_plant_types_are_valid():
    valid = {None, "coal", "gas", "nuclear", "solar", "wind", "hydro", "battery"}
    assert {p["grid_plant_type"] for p in PLANTS} <= valid
