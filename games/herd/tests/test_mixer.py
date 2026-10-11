"""GF-25 optional feed-additive mixer (FY-31: a small bonus, about 5% of a round's funds)."""

import json
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent.parent


def _result(env, quality):
    env.elements["mixer-result-button"].setAttribute("data-quality", str(quality))
    env.elements["mixer-result-button"].dispatch("click", None)


def _ready(env, funds=400.0):
    env.farm.funds = funds
    env.farm.decoupling_investment["feed"] = 1
    env.module.render()


def test_the_mixer_waits_for_the_first_feed_unit(game_env):
    m = game_env.module
    m.render()
    assert game_env.elements["mixer-start-button"].disabled and game_env.elements["mixer-auto-button"].disabled
    assert "unlocks" in game_env.elements["mixer-status"].innerText
    _ready(game_env)
    assert not game_env.elements["mixer-start-button"].disabled and not game_env.elements["mixer-auto-button"].disabled


def test_a_perfect_blend_pays_five_percent_of_the_funds(game_env):
    _ready(game_env, 400.0)
    _result(game_env, 1.0)
    assert game_env.farm.funds == pytest.approx(420.0)
    assert game_env.farm.mixer_blends == 1 and game_env.farm.mixer_perfects == 1
    assert "Perfect blend: +20.0 funds" in game_env.elements["mixer-note"].innerText


def test_the_bonus_never_beats_five_percent_or_the_hard_cap(game_env):
    m = game_env.module
    farm = game_env.farm
    farm.funds = 400.0
    assert farm.mixer_bonus_for(1.0) <= 400 * m.MIXER_BONUS_FRACTION + 1e-9
    farm.funds = 100000.0
    assert farm.mixer_bonus_for(1.0) == m.MIXER_BONUS_MAX
    farm.funds = -50.0
    assert farm.mixer_bonus_for(1.0) == 0.0
    farm.funds = 400.0
    assert farm.mixer_bonus_for(5.0) == farm.mixer_bonus_for(1.0) and farm.mixer_bonus_for(-1.0) == 0.0


def test_the_bonus_scales_with_quality_and_a_rough_blend_still_counts_as_a_blend(game_env):
    _ready(game_env, 400.0)
    _result(game_env, 0.5)
    assert game_env.farm.funds == pytest.approx(410.0)
    assert game_env.farm.mixer_perfects == 0 and game_env.farm.mixer_blends == 1
    assert "Good blend" in game_env.elements["mixer-note"].innerText


def test_one_blend_per_round_then_ready_again_after_advancing(game_env):
    _ready(game_env)
    _result(game_env, 1.0)
    funds = game_env.farm.funds
    _result(game_env, 1.0)  # a second try in the same round pays nothing
    assert game_env.farm.funds == funds and game_env.farm.mixer_blends == 1
    assert game_env.elements["mixer-start-button"].disabled
    game_env.advance_round()
    assert not game_env.elements["mixer-start-button"].disabled
    _result(game_env, 1.0)
    assert game_env.farm.mixer_blends == 2


def test_auto_blend_needs_no_timing_and_pays_half(game_env):
    _ready(game_env, 400.0)
    game_env.elements["mixer-auto-button"].dispatch("click", None)
    assert game_env.farm.funds == pytest.approx(410.0)
    assert "Auto-blend: +10.0 funds" in game_env.elements["mixer-note"].innerText
    assert game_env.farm.mixer_perfects == 0


def test_the_tally_is_visible_everywhere_it_should_be(game_env):
    m = game_env.module
    _ready(game_env, 400.0)
    assert "no blends yet" in game_env.elements["mixer-stats"].innerText
    _result(game_env, 0.95)
    stats = game_env.elements["mixer-stats"].innerText
    assert "1 blend, 1 perfect, +19.0 funds" in stats
    assert "Mixer tally" in m.report_card_html()


def test_junk_results_are_ignored_and_do_not_use_up_the_round(game_env):
    _ready(game_env)
    for junk in ("nan", "abc", "inf", "-inf", ""):
        _result(game_env, junk)
    assert game_env.farm.mixer_blends == 0 and game_env.farm.funds == 400.0
    assert game_env.farm.mixer_available()
    assert game_env.farm.blend(float("nan")) is None


def test_save_round_trip_and_validation(game_env):
    m = game_env.module
    assert "mixer_stats" not in m.get_state()
    _ready(game_env)
    _result(game_env, 1.0)
    state = json.loads(json.dumps(m.get_state()))
    assert state["mixer_stats"][0] == 1
    m.load_state({})
    assert m.farm.mixer_blends == 0
    m.load_state(state)
    assert (m.farm.mixer_blends, m.farm.mixer_perfects) == (1, 1) and m.farm.mixer_bonus_total > 0
    m.load_state({"mixer_stats": [3, 99, -5, "x"]})
    assert (m.farm.mixer_blends, m.farm.mixer_perfects, m.farm.mixer_bonus_total, m.farm.mixer_round) == (0, 0, 0.0, 0)
    m.load_state({"mixer_stats": [3, 99, -5, 2]})
    assert m.farm.mixer_perfects == 3 and m.farm.mixer_bonus_total == 0.0


def test_the_js_has_a_reduced_motion_path_and_a_keyboard_reachable_stop():
    js = (HERE / "settings.js").read_text(encoding="utf-8")
    assert "motionAllowed()" in js and "Use Auto-blend" in js and "stop.focus()" in js
    assert "MIXER_TIME = 5000" in js
    for page in ("index.html", "pc.html"):
        html = (HERE / page).read_text(encoding="utf-8")
        for rid in ("mixer-panel", "mixer-start-button", "mixer-stop-button", "mixer-auto-button", "mixer-result-button", "mixer-stats"):
            assert f'id="{rid}"' in html
        assert "Perfect" in html and "Good" in html  # zone labels are words, not only colours


def test_a_miss_still_pays_a_little(game_env):
    _ready(game_env, 400.0)
    _result(game_env, 0.0)
    assert game_env.farm.funds == pytest.approx(404.0)  # 20% of the 20-fund cap
    assert "Rough blend" in game_env.elements["mixer-note"].innerText
