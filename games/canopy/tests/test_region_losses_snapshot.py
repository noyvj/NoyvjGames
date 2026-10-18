"""data/region_losses.json: tree cover loss by driver for a boreal and a tropical group of countries (tools/fetch_region_losses.py)."""
import json
import re
from pathlib import Path

DATA = json.loads((Path(__file__).resolve().parent.parent / "data" / "region_losses.json").read_text(encoding="utf-8"))
COUNTRIES = DATA["countries"]


def test_source_and_date():
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", DATA["read"])
    for key in ("name", "publisher", "url", "csv_url", "citation", "licence"):
        assert DATA["source"][key]
    assert DATA["live"] is True and DATA["unit"].startswith("hectares")


def test_two_regions_and_five_countries_each_with_every_driver_every_year():
    assert set(DATA["regions"]) == {"boreal", "tropical"}
    assert sum(len(v) for v in DATA["regions"].values()) == 5 == len(COUNTRIES)
    assert len(DATA["drivers"]) == 7
    for name, c in COUNTRIES.items():
        assert len(c["years"]) >= 20 and "2001" in c["years"] and "2024" in c["years"], name
        for year, row in c["years"].items():
            assert list(row) == DATA["drivers"], (name, year)
            assert all(v is None or v >= 0 for v in row.values())


def test_the_computed_ten_year_totals_add_up_from_the_yearly_values():
    for name, c in COUNTRIES.items():
        years = sorted(c["years"])[-10:]
        assert c["ten_year_window"] == [years[0], years[-1]]
        for d in DATA["drivers"]:
            assert abs(sum(c["years"][y][d] or 0 for y in years) - c["ten_year_total_ha"][d]) < 0.01, (name, d)
        assert c["largest_driver"] == max(DATA["drivers"], key=lambda d: c["ten_year_total_ha"][d])


def test_the_main_cause_differs_between_the_boreal_and_the_tropics():
    assert COUNTRIES["Canada"]["largest_driver"] == "Wildfire" and COUNTRIES["Russia"]["largest_driver"] == "Wildfire"
    assert COUNTRIES["Brazil"]["largest_driver"] == "Permanent agriculture"
    assert COUNTRIES["Indonesia"]["largest_driver"] == "Permanent agriculture"
    assert COUNTRIES["Democratic Republic of Congo"]["largest_driver"] == "Shifting cultivation"
