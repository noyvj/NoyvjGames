"""data/solar_learning_curve.json: the frozen Our World in Data solar price curve (tools/fetch_solar_curve.py)."""
import json
import re
from pathlib import Path

DATA = json.loads((Path(__file__).resolve().parent.parent / "data" / "solar_learning_curve.json").read_text(encoding="utf-8"))


def test_every_snapshot_carries_its_source_and_date():
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", DATA["read"])
    src = DATA["source"]
    for key in ("name", "publisher", "url", "csv_url", "citation", "licence", "source_last_updated"):
        assert src[key], key
    assert src["url"].startswith("https://ourworldindata.org/")
    assert "US$" in DATA["price_unit"] and DATA["capacity_unit"] == "megawatts"


def test_rows_are_in_year_order_with_sane_numbers():
    rows = DATA["rows"]
    assert len(rows) >= 40
    years = [r["year"] for r in rows]
    assert years == sorted(set(years)) and years[0] == 1975
    for r in rows:
        assert set(r) == {"year", "price_usd_per_watt", "cumulative_capacity_mw"}
        assert 0 < r["price_usd_per_watt"] < 500
        assert r["cumulative_capacity_mw"] > 0


def test_price_fell_and_capacity_rose_over_the_whole_series():
    rows = DATA["rows"]
    assert rows[-1]["price_usd_per_watt"] < rows[0]["price_usd_per_watt"] / 100
    caps = [r["cumulative_capacity_mw"] for r in rows]
    assert caps == sorted(caps)
