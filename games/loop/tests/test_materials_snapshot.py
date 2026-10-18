"""data/materials.json: a Wikipedia fact for each of 24 materials, six per goods category (tools/fetch_materials.py)."""
import json
import re
from pathlib import Path

DATA = json.loads((Path(__file__).resolve().parent.parent / "data" / "materials.json").read_text(encoding="utf-8"))
MATERIALS = DATA["materials"]


def test_source_and_date():
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", DATA["read"])
    for key in ("name", "publisher", "url", "licence"):
        assert DATA["source"][key]
    assert "CC BY-SA" in DATA["source"]["licence"] and DATA["live"] is True


def test_six_materials_in_each_of_four_categories():
    cats = {}
    for m in MATERIALS:
        cats.setdefault(m["category"], []).append(m["material"])
    assert {k: len(v) for k, v in cats.items()} == {"electronics": 6, "clothing": 6, "furniture": 6, "shipyard": 6}
    assert len({m["material"] for m in MATERIALS}) == 24


def test_each_fact_is_a_short_extract_with_link_and_api():
    for m in MATERIALS:
        assert 40 <= len(m["fact"]) <= 600, m["material"]
        assert m["url"].startswith("https://en.wikipedia.org/wiki/")
        assert m["api"].startswith("https://en.wikipedia.org/api/rest_v1/page/summary/")
        assert m["revision"] and m["page_timestamp"]


def test_a_few_elements_carry_their_atomic_numbers():
    by = {m["material"]: m["fact"] for m in MATERIALS}
    assert "atomic number 29" in by["Copper"] and "atomic number 79" in by["Gold"] and "atomic number 26" in by["Iron"]
