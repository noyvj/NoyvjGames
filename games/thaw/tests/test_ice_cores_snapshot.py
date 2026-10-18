"""data/ice_cores.json: 30 NOAA ice core datasets, one per era (tools/fetch_ice_cores.py)."""
import json
import re
from pathlib import Path

DATA = json.loads((Path(__file__).resolve().parent.parent / "data" / "ice_cores.json").read_text(encoding="utf-8"))
CORES = DATA["ice_cores"]


def test_source_and_date():
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", DATA["read"])
    for key in ("name", "publisher", "url", "api", "licence"):
        assert DATA["source"][key]
    assert DATA["source"]["url"].startswith("https://www.ncei.noaa.gov/") and DATA["live"] is True


def test_thirty_distinct_cores_in_age_order():
    assert len(CORES) == 30
    assert len({c["site_name"] for c in CORES}) == 30
    ages = [c["dataset_oldest_year_bp"] for c in CORES]
    assert ages == sorted(ages)
    assert ages[0] < 1000 and ages[-1] > 700000


def test_every_core_carries_its_study_link_and_sane_numbers():
    for c in CORES:
        assert c["study_name"] and c["site_name"] and c["place"]
        assert c["study_url"] == "https://www.ncei.noaa.gov/access/paleo-search/study/%s" % c["noaa_study_id"]
        assert -90 <= c["latitude"] <= 90 and -180 <= c["longitude"] <= 180
        assert c["dataset_oldest_year_bp"] > c["dataset_newest_year_bp"]
        assert c["elevation_m"] is None or 0 <= c["elevation_m"] < 9000
        assert c["core_length_m"] is None or 0 < c["core_length_m"] < 4000
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", c["contribution_date"] or "0000-00-00") or c["contribution_date"] is None


def test_the_title_states_a_span_that_agrees_with_the_recorded_one():
    def stated(title):
        best = 0
        for m in re.finditer(r"(\d[\d,]*(?:\.\d+)?)\s*-?\s*(K\s?Yr|ka|Year|Yr)", title, re.I):
            best = max(best, float(m.group(1).replace(",", "")) * (1 if m.group(2).lower() in ("year", "yr") else 1000))
        return best
    for c in CORES:
        assert abs(stated(c["study_name"]) - c["dataset_oldest_year_bp"]) / c["dataset_oldest_year_bp"] <= 0.15, c["site_name"]


def test_known_cores_are_where_they_should_be():
    by = {c["site_name"]: c for c in CORES}
    assert by["EPICA Dome C"]["latitude"] < -70 and by["EPICA Dome C"]["dataset_oldest_year_bp"] > 800000
    assert by["Vostok"]["latitude"] < -75
