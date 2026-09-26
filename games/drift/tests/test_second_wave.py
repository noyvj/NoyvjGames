"""I25: the second, larger wave of arrivals."""

import pytest


def _ready(m):
    """A region past the minimum round with most arrivals integrated."""
    r = m.region
    r.round_number = m.SECOND_WAVE_MIN_ROUND
    r.total_arrivals = 100.0
    r.integrated_population = 100.0
    r.capacity.update({"housing": 1000.0, "services": 1000.0, "infrastructure": 1000.0})
    return r


def test_starts_with_no_wave(game_env):
    r = game_env.module.region
    assert r.second_wave_status is None and r.second_wave_result is None
    assert r.second_wave_message() == ""


def test_not_before_the_minimum_round(game_env):
    m = game_env.module
    r = _ready(m)
    r.round_number = m.SECOND_WAVE_MIN_ROUND - 2
    r.advance_round()
    assert r.second_wave_status is None


def test_not_before_arrivals_have_integrated(game_env):
    m = game_env.module
    r = _ready(m)
    r.capacity["services"] = 0.0  # nothing can integrate, so the fraction stays low
    r.integrated_population = 10.0
    r.advance_round()
    assert r.second_wave_status is None


def test_the_wave_is_announced_one_round_before(game_env):
    m = game_env.module
    r = _ready(m)
    r.advance_round()
    assert r.second_wave_status == "warned"
    assert "on its way" in r.second_wave_message()
    r.advance_round()
    assert r.second_wave_status == "active"
    with_wave = r.arrivals_this_round()
    r.second_wave_status = "done"
    assert with_wave == pytest.approx(r.arrivals_this_round() * m.SECOND_WAVE_ARRIVALS_MULTIPLIER)
    r.second_wave_status = "active"


def test_the_wave_lasts_a_fixed_number_of_rounds_then_ends(game_env):
    m = game_env.module
    r = _ready(m)
    r.advance_round()  # warned
    r.advance_round()  # active
    for _ in range(m.SECOND_WAVE_ROUNDS):
        assert r.second_wave_status == "active"
        r.advance_round()
    assert r.second_wave_status == "done"


def test_arrivals_are_doubled_only_while_active(game_env):
    m = game_env.module
    r = _ready(m)
    r.background_severity = 0.0
    normal = r.arrivals_this_round()
    r.second_wave_status = "active"
    assert r.arrivals_this_round() == normal * m.SECOND_WAVE_ARRIVALS_MULTIPLIER
    r.second_wave_status = "done"
    assert r.arrivals_this_round() == normal


def test_a_well_built_region_holds(game_env):
    m = game_env.module
    r = _ready(m)
    for _ in range(m.SECOND_WAVE_ROUNDS + 3):
        r.advance_round()
    assert r.second_wave_status == "done" and r.second_wave_result == "held"
    assert "held" in r.second_wave_message()


def test_an_underbuilt_region_is_strained(game_env):
    m = game_env.module
    r = _ready(m)
    r.total_arrivals = 100.0
    r.integrated_population = 80.0
    for _ in range(m.SECOND_WAVE_ROUNDS + 4):
        r.capacity.update({"housing": 0.0, "services": 5.0, "infrastructure": 0.0})
        r.advance_round()
    assert r.second_wave_status == "done" and r.second_wave_result == "strained"
    assert "wasn't enough" in r.second_wave_message()


def test_happens_only_once_per_region(game_env):
    m = game_env.module
    r = _ready(m)
    for _ in range(m.SECOND_WAVE_ROUNDS + 12):
        r.advance_round()
    assert r.second_wave_status == "done"
    r.advance_round()
    assert r.second_wave_status == "done"


def test_display_shows_and_hides(game_env):
    m = game_env.module
    m.render()
    assert game_env.elements["second-wave-display"].hidden is True
    m.region.second_wave_status = "warned"
    m.render()
    assert game_env.elements["second-wave-display"].hidden is False
    assert "on its way" in game_env.elements["second-wave-display"].innerText


def test_save_round_trip_and_default_omits_key(game_env):
    m = game_env.module
    assert "second_wave" not in m.get_state()
    r = m.region
    r.second_wave_status = "active"
    r.second_wave_rounds_left = 3
    r.second_wave_peak_strain = 0.4
    data = m.get_state()
    r.second_wave_status, r.second_wave_rounds_left, r.second_wave_peak_strain = None, 0, 0.0
    m.load_state(data)
    assert (r.second_wave_status, r.second_wave_rounds_left) == ("active", 3)
    assert r.second_wave_peak_strain == pytest.approx(0.4)


def test_done_result_round_trips(game_env):
    m = game_env.module
    m.region.second_wave_status = "done"
    m.region.second_wave_result = "held"
    data = m.get_state()
    m.region.second_wave_status = None
    m.load_state(data)
    assert m.region.second_wave_result == "held"


def test_load_rejects_bad_values(game_env):
    m = game_env.module
    base = m.get_state()
    for bad in (
        {"status": "bogus"}, {"status": 3}, "x", [1], None,
        {"status": "active", "rounds_left": 999, "peak_strain": 5},
        {"status": "active", "rounds_left": "2", "peak_strain": "x"},
        {"status": "done", "result": "weird"},
    ):
        data = dict(base)
        data["second_wave"] = bad
        m.load_state(data)
        r = m.region
        assert r.second_wave_status in (None, "active", "done")
        assert 0 <= r.second_wave_rounds_left <= m.SECOND_WAVE_ROUNDS
        assert 0.0 <= r.second_wave_peak_strain <= 1.0
        assert r.second_wave_result in (None, "held", "strained")
    data["second_wave"] = {"status": "bogus"}
    m.load_state(data)
    assert m.region.second_wave_status is None
