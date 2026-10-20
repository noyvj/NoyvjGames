"""Edge-case tests for bodies.py: limits, zero inputs, and boundaries using real game data."""

import json
import math
from pathlib import Path

import bodies
import bodies_data as D

GAME_DIR = Path(__file__).resolve().parent.parent
SNAP = json.loads((GAME_DIR / "data" / "snapshot.json").read_text(encoding="utf-8"))


def test_soi_radius_with_zero_a_km_returns_zero():
    """soi_radius should return 0 when the orbital radius is zero."""
    assert bodies.soi_radius(0.0, D.GM_SUN, D.PLANETS["earth"][0]) == 0.0


def test_soi_radius_with_real_planet_data_matches_expected_sizes():
    """SOI radii for Earth and Mars should match the known sizes from the snapshot."""
    earth_gm = D.PLANETS["earth"][0]
    mars_gm = D.PLANETS["mars"][0]
    au = D.AU_KM
    earth_soi = bodies.soi_radius(au, earth_gm, D.GM_SUN)
    assert abs(earth_soi - 925000) < 10000
    mars_a = D.PLANETS["mars"][2] * au
    mars_soi = bodies.soi_radius(mars_a, mars_gm, D.GM_SUN)
    assert abs(mars_soi - 577000) < 5000


def test_julian_date_handles_smallest_and_largest_valid_years():
    """julian_date should handle year 1 and year 9999 without error or overflow."""
    jd_start = bodies.julian_date(1, 1, 1)
    jd_end = bodies.julian_date(9999, 12, 31)
    assert jd_start > 0
    assert jd_end > jd_start
    assert abs(jd_start - 1721425.5) < 0.5


def test_label_and_label_plain_for_special_names():
    """label and label_plain must return correct strings for 'sun' and 'moon', and capitalize others."""
    assert bodies.label("sun") == "the Sun"
    assert bodies.label("moon") == "the Moon"
    assert bodies.label("mars") == "Mars"
    assert bodies.label_plain("sun") == "Sun"
    assert bodies.label_plain("moon") == "Moon"
    assert bodies.label_plain("mars") == "Mars"


def test_planet_angle_with_j2000_and_far_future_date():
    """planet_angle should return the correct angle at J2000 and handle large jd values."""
    expected_rad = math.radians(D.PLANETS["earth"][3])
    actual_rad = bodies.planet_angle("earth", bodies.J2000)
    assert abs(actual_rad - expected_rad) < 1e-9
    far_jd = bodies.julian_date(3000, 1, 1)
    angle = bodies.planet_angle("earth", far_jd)
    assert isinstance(angle, float)


def test_period_seconds_with_planet_data():
    """period_seconds should compute a positive period for any planet with n > 0."""
    for name in D.PLANETS:
        p = bodies.planet(name)
        period = bodies.period_seconds(p)
        assert period > 0, f"Period for {name} is not positive"
        assert abs(period - 2.0 * math.pi / p["n"]) < 1e-6
