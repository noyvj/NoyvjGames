"""data/forest_carbon.json: FAO per-hectare forest carbon and OWID/FAO above-ground biomass (tools/fetch_forest_carbon.py)."""
import json
import re
from pathlib import Path

DATA = json.loads((Path(__file__).resolve().parent.parent / "data" / "forest_carbon.json").read_text(encoding="utf-8"))
FAO = DATA["fao_fra2020"]
OWID = DATA["owid_above_ground_biomass"]


def test_source_and_date():
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", DATA["read"])
    for block in (FAO, OWID):
        assert block["publisher"] and block["licence"] and block["url" if "url" in block else "chart_url"].startswith("https://")
    assert FAO["live"] is False and OWID["live"] is True


def test_fao_numbers_are_the_ones_in_the_quoted_sentences():
    text = " ".join(FAO["exact_sentences"])
    assert FAO["carbon_density_t_per_ha"] == {"1990": 159.0, "2020": 163.0} and "159 tonnes to 163 tonnes per ha" in text
    assert FAO["carbon_stock_gt"] == {"1990": 668.0, "2020": 662.0} and "668 gigatonnes in 1990 to 662 gigatonnes in 2020" in text
    assert "4.06 billion hectares" in text and FAO["forest_area_billion_ha"] == 4.06
    assert FAO["living_biomass_gt"] == 606.0 and FAO["share_of_forest_carbon_in_living_biomass_percent"] == 44.0


def test_density_matches_stock_over_area_within_rounding():
    density = FAO["carbon_stock_gt"]["2020"] / FAO["forest_area_billion_ha"]
    assert abs(density - FAO["carbon_density_t_per_ha"]["2020"]) < 1.0


def test_owid_countries_are_sane_and_tropics_beat_the_boreal():
    latest = OWID["latest"]
    assert OWID["unit"] == "tonnes per hectare" and OWID["csv_url"].endswith(".csv")
    for name, row in latest.items():
        assert 2015 <= row["year"] <= 2030 and 20 < row["above_ground_biomass_t_per_ha"] < 400, name
    assert latest["Brazil"]["above_ground_biomass_t_per_ha"] > latest["Canada"]["above_ground_biomass_t_per_ha"]
    assert latest["Democratic Republic of Congo"]["above_ground_biomass_t_per_ha"] > latest["Finland"]["above_ground_biomass_t_per_ha"]


def test_the_co2_ratio_is_written_as_a_formula_not_a_measurement():
    assert "44.01 / 12.011" in DATA["co2_per_carbon"]["formula"]
