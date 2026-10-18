"""data/transfer_data.json: the frozen NASA/JPL orbit numbers for transfer windows (tools/fetch_transfer_data.py)."""
import json
import math
import re
from pathlib import Path

DATA = json.loads((Path(__file__).resolve().parent.parent / "data" / "transfer_data.json").read_text(encoding="utf-8"))
BY_WORLD = {b["world"]: b for b in DATA["bodies"]}
WORLDS = {"Earth", "Mars", "Moon", "Venus", "AsteroidBelt", "Pluto", "JupiterMoons", "SaturnMoons"}


def test_source_and_date():
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", DATA["read"])
    assert DATA["publisher"] and DATA["licence"] and DATA["live"] is False
    assert len(DATA["sources"]) == 5 and all(s["url"].startswith("https://ssd") for s in DATA["sources"])


def test_every_sol_world_has_a_body():
    assert set(BY_WORLD) == WORLDS


def test_sun_constants():
    assert abs(DATA["gm_sun_km3_s2"] - 1.32712440041e11) < 1e5
    assert DATA["astronomical_unit_km"] == 149597870.7


def test_distances_increase_outward_and_periods_agree_with_keplers_third_law():
    order = ["Venus", "Earth", "Mars", "AsteroidBelt", "JupiterMoons", "SaturnMoons", "Pluto"]
    a = [BY_WORLD[w]["semi_major_axis_au"] for w in order]
    assert a == sorted(a)
    for w in order:
        b = BY_WORLD[w]
        years = b.get("orbital_period_years") or b["orbital_period_days"] / 365.25
        assert abs(years - b["semi_major_axis_au"] ** 1.5) / years < 0.01, w


def test_the_moon_orbits_earth():
    moon = BY_WORLD["Moon"]
    assert moon["orbits"] == "Earth" and moon["semi_major_axis_km"] == 384400.0 and 27 < moon["orbital_period_days"] < 28
    assert math.isclose(moon["semi_major_axis_km"] / DATA["astronomical_unit_km"], 0.00257, rel_tol=0.01)
