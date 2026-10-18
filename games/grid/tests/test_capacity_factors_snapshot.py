"""data/capacity_factors.json: the frozen EIA Electric Power Monthly capacity factors (tools/fetch_capacity_factors.py)."""
import json
import re
from pathlib import Path

DATA = json.loads((Path(__file__).resolve().parent.parent / "data" / "capacity_factors.json").read_text(encoding="utf-8"))
BY_LABEL = {t["label"]: t for table in DATA["tables"] for t in table["technologies"]}


def test_source_and_date_are_on_the_file_and_each_table():
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", DATA["read"])
    for key in ("name", "publisher", "url", "licence"):
        assert DATA["source"][key]
    assert len(DATA["tables"]) == 2
    for table in DATA["tables"]:
        assert table["url"].startswith("https://www.eia.gov/") and table["data_for"] and table["release_date"]


def test_the_plants_grid_needs_are_present():
    for label in ("Coal", "Natural gas: combined cycle", "Nuclear", "Solar: photovoltaic", "Wind", "Hydroelectric"):
        assert label in BY_LABEL, label


def test_every_year_row_is_sane_and_in_order():
    for label, tech in BY_LABEL.items():
        years = [r["year"] for r in tech["annual"]]
        assert years == sorted(set(years)) and len(years) >= 8, label
        for r in tech["annual"]:
            assert 0 < r["capacity_factor_pct"] <= 100, (label, r)
            assert r["capacity_mw"] > 0, (label, r)


def test_the_headline_ordering_a_player_should_learn_holds():
    last = {label: t["annual"][-1]["capacity_factor_pct"] for label, t in BY_LABEL.items()}
    assert last["Nuclear"] > 85
    assert last["Solar: photovoltaic"] < 30 < last["Nuclear"]
    assert last["Wind"] < last["Nuclear"]
