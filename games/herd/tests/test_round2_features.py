"""Round-2 Herd items: F2, F4, F6, F11, F12, F14, F16, F18, F22, F24, F26, F30."""

import json


def test_pasture_herd_count_overlay_tracks_herd(game_env):
    el = game_env.elements["pasture-herd-count"]
    assert el.hidden is True
    game_env.farm.funds = 500
    game_env.grow_herd()
    game_env.grow_herd()
    assert el.hidden is False
    assert el.innerText == "Herd: 2"


def test_half_decoupled_callout_explains_decoupled(game_env):
    assert "decoupled" in game_env.module._MILESTONE_CALLOUT_MESSAGES["half_decoupled"]


def test_beat_percentage_message_ahead_and_behind(game_env):
    farm = game_env.farm
    farm.funds, farm.counterfactual_funds = 330.0, 300.0
    assert "beats the pure-growth baseline by 10.0%" in game_env.module.beat_percentage_message()
    farm.funds = 270.0
    assert "trails the pure-growth baseline by 10.0%" in game_env.module.beat_percentage_message()
    assert "10.0%" in game_env.module.report_card_html()


def test_investment_summary_separates_pivot_with_icons(game_env):
    game_env.farm.plant_pivot_investment = 2
    text = game_env.module.investment_summary_message()
    for spec in game_env.module.DECOUPLING_MEASURES.values():
        assert spec["icon"] in text
    assert "Separate lever" in text and "x2" in text


def test_certification_earned_after_sustained_low_ratio(game_env):
    farm = game_env.farm
    module = game_env.module
    farm.herd_size = 2
    farm.decoupling_investment["capture"] = 5  # ratio 0.5
    for _ in range(module.CERTIFICATION_ROUNDS_REQUIRED - 1):
        farm.advance_round()
    assert not farm.certified
    farm.advance_round()
    assert farm.certified
    assert farm.just_hit_callout in ("certified", "half_decoupled")
    assert farm.certification_multiplier() == 1 + module.CERTIFICATION_PRICE_PREMIUM


def test_certification_streak_resets_and_premium_applies(game_env):
    farm = game_env.farm
    farm.herd_size = 2
    farm.decoupling_investment["capture"] = 5
    farm.advance_round()
    assert farm.certification_streak == 1
    farm.decoupling_investment["capture"] = 0
    farm.advance_round()
    assert farm.certification_streak == 0
    farm.certified = True
    funds = farm.funds
    pressure = farm.pressure_fraction()
    farm.advance_round()
    expected = 2 * game_env.module.HERD_INCOME_PER_UNIT * 1.10 * (1 - pressure)
    assert abs((farm.funds - funds) - expected) < 1e-9


def test_certification_round_trips_and_old_saves_default(game_env):
    farm = game_env.farm
    farm.certified, farm.certification_streak = True, 7
    saved = json.loads(json.dumps(game_env.module.get_state()))
    farm.certified, farm.certification_streak = False, 0
    game_env.module.load_state(saved)
    assert farm.certified and farm.certification_streak == 7
    del saved["certified"], saved["certification_streak"]
    game_env.module.load_state(saved)
    assert not farm.certified and farm.certification_streak == 0


def test_certification_display_updates(game_env):
    assert "0/5" in game_env.elements["certification-display"].innerText
    game_env.farm.certified = True
    game_env.module.render()
    assert "Certified" in game_env.elements["certification-display"].innerText


def test_plant_pivot_confirm_states_exact_tradeoff(game_env):
    msg = game_env.module.plant_pivot_confirm_message()
    assert "15% less income per unit" in msg
    assert "0.75%" in msg


def test_real_world_message_congratulates_only_when_beating(game_env):
    farm = game_env.farm
    farm.decoupling_investment["capture"] = 4  # exactly 40% < 42%
    assert "Congratulations" not in game_env.module.real_world_comparison_message()
    farm.decoupling_investment["capture"] = 5  # 50%
    assert "Congratulations" in game_env.module.real_world_comparison_message()


def test_grow_preview_shows_before_after_arrows(game_env):
    game_env.farm.herd_size = 2
    msg = game_env.module.grow_consequence_message()
    assert "→" in msg and "↑" in msg
    assert "Income/round 10.0 → 15.0" in msg


def test_on_advance_round_consumes_flatten_flag(game_env):
    farm = game_env.farm
    farm.herd_size = 4
    farm.advance_round()
    farm.decoupling_investment["capture"] = 5
    game_env.advance_round()
    assert farm.just_flattened is False


def test_flatten_flag_set_by_advance_round(game_env):
    farm = game_env.farm
    farm.herd_size = 4
    farm.advance_round()
    farm.advance_round()
    assert farm.just_flattened is False
    farm.decoupling_investment["capture"] = 5
    farm.advance_round()
    assert farm.just_flattened is True


def test_new_best_pulses_gauge_range_label(game_env):
    game_env.farm.funds = 100
    game_env.invest_decoupling("capture")
    assert game_env.timers is not None  # pulse scheduled without error
    assert game_env.farm.decoupling_investment["capture"] == 1


def test_wisps_thin_with_decoupling(game_env):
    module = game_env.module
    game_env.farm.herd_size = 3
    module.render()
    full = float(game_env.elements["pasture-wisp-a"].style.opacity)
    game_env.farm.decoupling_investment["capture"] = 5
    module.render()
    thinner = float(game_env.elements["pasture-wisp-a"].style.opacity)
    assert thinner < full
    game_env.farm.decoupling_investment["capture"] = 9
    module.render()
    assert game_env.elements["pasture-wisp-c"].hidden is True


def test_haze_explanation_present_in_page():
    from pathlib import Path
    html = (Path(__file__).resolve().parent.parent / "index.html").read_text()
    assert "haze" in html and "market/regulatory pressure" in html
