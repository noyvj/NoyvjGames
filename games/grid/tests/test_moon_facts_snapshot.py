"""data/moon_facts.json: the frozen NASA Moon Fact Sheet numbers (tools/fetch_moon_facts.py)."""
import json
import re
from pathlib import Path

DATA = json.loads((Path(__file__).resolve().parent.parent / "data" / "moon_facts.json").read_text(encoding="utf-8"))
FACTS = {f["key"]: f for f in DATA["facts"]}


def test_source_and_dates():
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", DATA["read"]) and DATA["page_last_updated"]
    for key in ("name", "publisher", "url", "licence"):
        assert DATA["source"][key]
    assert DATA["source"]["url"].startswith("https://nssdc.gsfc.nasa.gov/")
    assert DATA["live"] is False


def test_every_fact_has_a_unit_and_the_printed_text_matches_the_number():
    for f in DATA["facts"]:
        assert f["unit"] and f["label"]
        assert float(f["printed"]) == f["value"]


def test_the_lunar_day_numbers_are_there_and_sane():
    assert FACTS["synodic_period"]["value"] == 29.53
    assert 650 < FACTS["sidereal_rotation_period"]["value"] < 660
    assert abs(FACTS["sidereal_rotation_period"]["value"] / 24 - FACTS["revolution_period"]["value"]) < 0.1
    assert FACTS["diurnal_temperature_min"]["value"] < FACTS["diurnal_temperature_max"]["value"]
    assert 1300 < FACTS["solar_irradiance"]["value"] < 1400
    assert 1.5 < FACTS["surface_gravity"]["value"] < 1.7
