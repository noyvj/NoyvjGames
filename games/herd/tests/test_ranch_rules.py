"""F-1 Ranch Rules (planning/TODO.md "GF + F. Herd", FY-32): four balance sliders, custom runs are unranked."""

import json
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent.parent


def _slide(env, name, value):
    el = env.elements["rule-" + name.replace("_", "-")]
    el.value = str(value)
    el.dispatch("input", None)


def test_standard_rules_change_nothing(game_env):
    m = game_env.module
    assert not m.rules_are_custom()
    assert game_env.farm.funds == m.STARTING_FUNDS
    assert game_env.farm.grow_herd_cost() == m.HERD_GROWTH_COST
    assert m.pressure_scale() == m.PRESSURE_SCALE
    assert not m.rules_unranked()
    assert "ranch_rules" not in m.get_state() and "custom_rules_used" not in m.get_state()


def test_starting_funds_moves_a_fresh_farm_and_its_baseline(game_env):
    m = game_env.module
    _slide(game_env, "starting_funds", 450)
    assert game_env.farm.funds == 450 and game_env.farm.counterfactual_funds == 450
    assert game_env.farm.funds_history[0] == 450
    assert m.rules_unranked()


def test_starting_funds_after_play_waits_for_the_next_farm(game_env):
    m = game_env.module
    game_env.grow_herd()
    funds = game_env.farm.funds
    _slide(game_env, "starting_funds", 500)
    assert game_env.farm.funds == funds
    assert m.FarmState().funds == 500  # a new farm (handover) starts on the new purse
    assert "next new farm" in game_env.elements["rules-start-note"].innerText


def test_growth_slope_changes_the_price_of_the_next_unit(game_env):
    game_env.farm.herd_size = 4
    _slide(game_env, "growth_slope", 0)
    assert game_env.farm.grow_herd_cost() == game_env.module.HERD_GROWTH_COST
    _slide(game_env, "growth_slope", 4)
    assert game_env.farm.grow_herd_cost() == game_env.module.HERD_GROWTH_COST + 16


def test_pressure_strength_scales_pressure_for_the_farm_and_the_baseline(game_env):
    farm = game_env.farm
    farm.methane = 50.0
    farm.counterfactual_methane = 50.0
    assert farm.pressure_fraction() == pytest.approx(0.5)
    _slide(game_env, "pressure_strength", 150)
    assert farm.pressure_fraction() == pytest.approx(0.75)
    assert farm.counterfactual_pressure_fraction() == pytest.approx(0.75)
    _slide(game_env, "pressure_strength", 50)
    assert farm.pressure_fraction() == pytest.approx(0.25)


def test_season_swing_scales_the_income_swing_and_the_calendar(game_env):
    m = game_env.module
    farm = game_env.farm
    farm.variation_enabled = True
    farm.round_number = 2  # a +-5% or larger season round
    raw = m.season_for_round(2)[1]
    _slide(game_env, "season_swing", 200)
    assert farm.season_modifier() == pytest.approx(raw * 2)
    cell = m.season_calendar_cells()[0]
    assert cell["mod"] == pytest.approx(raw * 2) and cell["raw"] == raw
    _slide(game_env, "season_swing", 0)
    assert farm.season_modifier() == 0
    assert m.season_calendar_html()  # still draws with a zero swing


def test_values_are_clamped_and_snapped(game_env):
    m = game_env.module
    assert m.clean_rule_value("starting_funds", 99999) == 600
    assert m.clean_rule_value("starting_funds", 337) == 350
    assert m.clean_rule_value("growth_slope", -3) == 0
    assert m.clean_rule_value("season_swing", "100") is None
    assert m.clean_rule_value("season_swing", float("nan")) is None
    assert m.clean_rule_value("nonsense", 1) is None
    assert m.clean_rule_value("starting_funds", True) is None


def test_custom_runs_are_unranked_everywhere(game_env):
    m = game_env.module
    calls = []

    class Board:
        def report(self, *args):
            calls.append(("board", args))

    class Window:
        NoyvjLeaderboard = Board()

        def herdCompare(self, *args):
            calls.append(("compare", args))

    import sys
    sys.modules["js"].window = Window()
    # A standard run that is ahead of its baseline reports to both hooks...
    game_env.farm.herd_size = 5
    game_env.farm.counterfactual_funds = -100
    m._report_decoupling_gap()
    m._request_comparison()
    assert {c[0] for c in calls} == {"board", "compare"}
    calls.clear()
    # ...a custom-rules run reports to neither.
    _slide(game_env, "growth_slope", 1)
    m._report_decoupling_gap()
    m._request_comparison()
    assert calls == []
    assert "unranked" in m.report_card_html()
    assert "unranked" in m.copy_result_fields()["stats"][-1]
    assert game_env.elements["rules-badge"].hidden is False


def test_a_run_that_used_custom_rules_stays_unranked_after_a_reset(game_env):
    m = game_env.module
    game_env.grow_herd()
    _slide(game_env, "growth_slope", 1)
    game_env.elements["rules-reset-button"].dispatch("click", None)
    assert not m.rules_are_custom()
    assert m.rules_unranked()
    assert "stays unranked" in game_env.elements["rules-summary"].innerText


def test_back_to_standard_on_a_fresh_farm_clears_the_flag(game_env):
    m = game_env.module
    _slide(game_env, "starting_funds", 400)
    game_env.elements["rules-reset-button"].dispatch("click", None)
    assert not m.rules_unranked()
    assert game_env.farm.funds == m.STARTING_FUNDS


def test_score_400_cannot_be_earned_on_custom_rules(game_env):
    m = game_env.module
    _slide(game_env, "starting_funds", 600)
    assert game_env.farm.score() >= m.SCORE_400_TARGET
    assert not m.ACHIEVEMENT_CHECKS["score_400"]()


def test_rules_ride_the_save_only_when_custom_and_load_back(game_env):
    m = game_env.module
    _slide(game_env, "growth_slope", 1)
    game_env.grow_herd()
    state = m.get_state()
    assert state["ranch_rules"] == {"growth_slope": 1.0} and state["custom_rules_used"] is True
    json.dumps(state)
    game_env.elements["rules-reset-button"].dispatch("click", None)
    m.load_state(state)
    assert m.rule("growth_slope") == 1.0 and m.rules_unranked()
    # a standard save puts the standard rules back
    standard = {"round_number": 2, "funds": 100}
    m.load_state(standard)
    assert not m.rules_are_custom()
    assert not m.farm.custom_rules_used


def test_bad_rule_values_in_a_save_are_ignored(game_env):
    m = game_env.module
    m.load_state({"ranch_rules": {"growth_slope": "lots", "starting_funds": 99999, "bogus": 1}, "custom_rules_used": "yes"})
    assert m.rule("growth_slope") == 2.0 and m.rule("starting_funds") == 600
    m.load_state({"ranch_rules": "nope"})
    assert not m.rules_are_custom()


def test_rules_are_remembered_in_the_browser_for_a_new_farm(game_env):
    _slide(game_env, "season_swing", 150)
    stored = json.loads(game_env.local_storage.getItem("herd-ranch-rules"))
    assert stored["season_swing"] == 150
    module = game_env.reload()
    assert module.rule("season_swing") == 150
    assert module.farm.custom_rules_used


def test_a_handover_keeps_the_rules(game_env):
    m = game_env.module
    _slide(game_env, "growth_slope", 3)
    game_env.farm.certified = True
    m.hand_over_farm()
    assert m.rule("growth_slope") == 3.0 and m.farm.custom_rules_used


def test_both_pages_carry_the_rule_controls():
    for page in ("index.html", "pc.html"):
        html = (HERE / page).read_text(encoding="utf-8")
        for rid in ("rule-starting-funds", "rule-season-swing", "rule-pressure-strength", "rule-growth-slope",
                    "rules-summary", "rules-reset-button", "rules-badge"):
            assert f'id="{rid}"' in html
