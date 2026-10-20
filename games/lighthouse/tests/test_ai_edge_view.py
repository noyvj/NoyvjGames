"""Edge-case tests for view.py functions."""

import data
import sim
from state import Keep
from view import rep_title, rep_next, part_state, sky_for, forecast_view, build


def keep_at(night=1, seed=3):
    k = Keep(seed)
    k.night = night
    sim.to_evening(k)
    return k


def test_rep_title_handles_negative_and_large_values():
    assert rep_title(-10) == data.REP_TITLES[0][1]
    assert rep_title(0) == data.REP_TITLES[0][1]
    first_thresh = data.REP_TITLES[0][0]
    assert rep_title(first_thresh) == data.REP_TITLES[0][1]
    last_thresh = data.REP_TITLES[-1][0]
    assert rep_title(last_thresh) == data.REP_TITLES[-1][1]
    assert rep_title(999999) in [name for _, name in data.REP_TITLES]


def test_rep_next_returns_correct_threshold_or_none():
    assert rep_next(-10)["at"] == data.REP_TITLES[0][0]
    # rep_next returns the first threshold strictly greater than points
    nxt_zero = rep_next(0)
    assert nxt_zero["at"] > 0
    if len(data.REP_TITLES) > 1:
        first_thresh = data.REP_TITLES[0][0]
        nxt = rep_next(first_thresh)
        assert nxt["at"] == data.REP_TITLES[1][0]
    assert rep_next(999999) is None


def test_part_state_clamps_at_boundaries():
    assert part_state(-1) == "failing"
    assert part_state(0) == "failing"
    assert part_state(14) == "failing"
    assert part_state(15) == "poor"
    assert part_state(39) == "poor"
    assert part_state(40) == "worn"
    assert part_state(69) == "worn"
    assert part_state(70) == "sound"
    assert part_state(100) == "sound"


def test_sky_for_respects_all_phases():
    k = keep_at()
    for phase, expected in [("night", "night"), ("evening", "dusk"), ("morning", "dawn"), ("day", "day")]:
        k.phase = phase
        assert sky_for(k) == expected
    k.phase = "yearend"
    assert sky_for(k) == "day"
    k.phase = None
    assert sky_for(k) == "day"


def test_forecast_view_returns_valid_structure_and_night():
    for night in (1, 20, 40):
        k = keep_at(night)
        v = forecast_view(k, night)
        assert v["night"] == night
        assert isinstance(v["lo"], int) and isinstance(v["hi"], int)
        assert isinstance(v["lo_label"], str)
        assert isinstance(v["hi_label"], str)
        assert v["narrow"] == (v["lo"] == v["hi"])


def test_build_handles_empty_settings_and_minimal_keep():
    k = keep_at(1)
    v = build(k, {})
    assert v["phase"] == "evening"
    assert v["night"] == 1
    assert isinstance(v["oil"], (int, float))
    assert isinstance(v["supplies"], list)

    v2 = build(k, {"eerie": False})
    assert v2["eerie"] is False

    k.oil = -5.0
    v3 = build(k, {})
    assert v3["oil"] == -5.0
