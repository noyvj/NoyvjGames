"""The real numbers: the generated data matches the dated snapshot, and the circles the game draws match their sources."""

import json
import math
from pathlib import Path

import bodies
import bodies_data as D

GAME_DIR = Path(__file__).resolve().parent.parent
SNAP = json.loads((GAME_DIR / "data" / "snapshot.json").read_text(encoding="utf-8"))


def test_the_generated_data_is_the_snapshot():
    assert D.READ == SNAP["read"] == "2026-10-12"
    assert D.GM_SUN == SNAP["gm_sun"] and D.AU_KM == SNAP["au_km"]
    for name, p in SNAP["planets"].items():
        assert D.PLANETS[name.lower()] == (p["gm"], p["radius_km"], p["a_au"], p["L0_deg"], p["Ldot_deg_per_cy"], p["orbital_period_y"])
    for name, m in SNAP["moons"].items():
        assert D.MOONS[name.lower()] == (m["planet"].lower(), m["gm"], m["radius_km"], m["a_km"], m["period_d"])


def test_a_few_values_against_what_the_sources_say():
    assert abs(D.GM_SUN - 1.32712440041e11) < 1e3                 # JPL DE440
    assert D.AU_KM == 149597870.7                                  # IAU 2012
    assert D.PLANETS["earth"][1] == 6371.0084 and D.PLANETS["mars"][1] == 3389.5
    assert D.MOONS["moon"][2] == 1737.4 and D.MOONS["phobos"][2] == 11.08 and D.MOONS["deimos"][2] == 6.2
    assert D.MOONS["moon"][3] == 384400.0 and D.MOONS["phobos"][3] == 9375.0 and D.MOONS["deimos"][3] == 23457.0
    assert abs(D.PLANETS["venus"][2] - 0.72333566) < 1e-9


def test_each_planets_period_from_the_circle_matches_its_source_to_a_third_of_a_percent():
    for name, row in D.PLANETS.items():
        p = bodies.planet(name)
        period_y = 2 * math.pi / p["n"] / 86400.0 / 365.25
        assert abs(period_y / row[5] - 1) < 0.003, (name, period_y, row[5])


def test_each_moons_period_from_the_circle_matches_its_source_to_one_percent():
    for name, row in D.MOONS.items():
        m = bodies.moon(name)
        period_d = 2 * math.pi / m["n"] / 86400.0
        assert abs(period_d / row[4] - 1) < 0.01, (name, period_d, row[4])


def test_spheres_of_influence_are_the_usual_sizes():
    assert abs(bodies.moon("moon")["soi"] - 66000) < 1000
    assert abs(bodies.planet("earth")["soi"] - 925000) < 10000
    assert abs(bodies.planet("mars")["soi"] - 577000) < 5000
    assert abs(bodies.planet("venus")["soi"] - 616000) < 5000
    assert bodies.moon("phobos")["soi"] < bodies.moon("phobos")["radius"] * 1.0 + 1.0          # too small to matter


def test_julian_date_and_the_planets_start_angles():
    assert bodies.julian_date(2000, 1, 1) == 2451544.5
    assert bodies.julian_date(2026, 10, 1) == 2461314.5
    # at J2000 each planet is at its table longitude
    assert abs(math.degrees(bodies.planet_angle("earth", bodies.J2000)) - 100.46457166) < 1e-9
    # Mars leads Earth by about 44 degrees in mid-November 2026: the Hohmann window the missions are built around
    lead = math.degrees(bodies.planet_angle("mars", bodies.julian_date(2026, 11, 18)) - bodies.planet_angle("earth", bodies.julian_date(2026, 11, 18))) % 360.0
    assert 40 < lead < 48


def test_the_source_dates_are_all_on_screen_and_in_sources_json():
    sources = json.loads((GAME_DIR / "sources.json").read_text(encoding="utf-8"))
    assert all(r["read"] == D.READ for r in sources["research"])
    urls = " ".join(r["url"] for r in sources["research"])
    for needle in ("astro_par", "approx_pos", "planets/phys_par", "sats/phys_par", "sats/elem", "factsheet"):
        assert needle in urls
