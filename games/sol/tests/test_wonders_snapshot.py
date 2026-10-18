"""data/wonders.json: 41 named sights with a NASA-written fact each (tools/fetch_wonders.py)."""
import json
import re
from pathlib import Path

DATA = json.loads((Path(__file__).resolve().parent.parent / "data" / "wonders.json").read_text(encoding="utf-8"))
WONDERS = DATA["wonders"]
WORLDS = {"Earth", "Mars", "Moon", "Venus", "AsteroidBelt", "Pluto", "JupiterMoons", "SaturnMoons"}


def test_source_and_date():
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", DATA["read"])
    for key in ("name", "publisher", "url", "licence"):
        assert DATA["source"][key]
    assert DATA["live"] is True


def test_forty_one_sights_with_unique_names_in_every_world():
    assert len(WONDERS) == 41
    assert len({w["name"] for w in WONDERS}) == 41
    assert {w["world"] for w in WONDERS} == WORLDS


def test_every_sight_has_its_fact_source_and_date():
    for w in WONDERS:
        assert 40 <= len(w["fact"]) <= 700, w["name"]
        assert w["url"].startswith("https://science.nasa.gov/"), w["name"]
        assert w["api"].startswith("https://science.nasa.gov/wp-json/wp/v2/") and w["slug"] in w["api"]
        assert re.match(r"\d{4}-\d{2}-\d{2}T", w["page_modified"]) and w["nasa_title"]
        assert w["cut_short"] == w["fact"].endswith("[…]")
        assert "<" not in w["fact"] and "&#" not in w["fact"]


def test_a_few_facts_are_copied_exactly():
    by = {w["name"]: w for w in WONDERS}
    assert "largest known volcano in the Solar System" in by["Olympus Mons"]["fact"]
    assert "2,500 miles long" in by["Valles Marineris"]["fact"]
    assert "highest mountain on Venus" in by["Maxwell Montes"]["fact"]
    assert "more than 300 bright areas" in by["Ceres' bright spots"]["fact"]
