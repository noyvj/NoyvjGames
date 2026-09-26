"""H9: waste stream diversification (focus one circularity measure for a bonus)."""

import pytest


def _click(env, measure):
    env.elements[f"focus-{measure}-button"].dispatch("click", None)


def test_no_focus_by_default(game_env):
    m = game_env.module
    assert game_env.chain.waste_focus is None
    for measure in m.CIRCULARITY_INVESTMENTS:
        assert game_env.chain.measure_multiplier(measure) == 1.0


def test_focus_boosts_only_that_measure(game_env):
    m = game_env.module
    c = game_env.chain
    c.circularity_investment.update({"repair": 2, "reuse": 2, "recycle": 2})
    base = c.internal_circular_supply()
    c.set_waste_focus("reuse")
    extra = 2 * m.CIRCULARITY_INVESTMENTS["reuse"]["supply_per_unit"] * m.WASTE_STREAM_SPECIALIZATION_BONUS
    assert c.internal_circular_supply() == pytest.approx(base + extra)
    assert c.measure_multiplier("repair") == 1.0 and c.measure_multiplier("recycle") == 1.0


def test_only_one_focus_at_a_time(game_env):
    c = game_env.chain
    c.set_waste_focus("repair")
    c.set_waste_focus("recycle")
    assert c.waste_focus == "recycle"
    assert c.measure_multiplier("repair") == 1.0


def test_unknown_focus_rejected(game_env):
    c = game_env.chain
    for bad in ("bogus", "", 3, ["repair"]):
        assert c.set_waste_focus(bad) is False
    assert c.waste_focus is None


def test_focus_can_be_cleared(game_env):
    c = game_env.chain
    c.set_waste_focus("reuse")
    assert c.set_waste_focus(None) is True and c.waste_focus is None


def test_button_toggles_focus_on_and_off(game_env):
    _click(game_env, "recycle")
    assert game_env.chain.waste_focus == "recycle"
    assert game_env.elements["focus-recycle-button"].classList.contains("focus-button--on")
    assert "Focused" in game_env.elements["focus-recycle-button"].innerText
    _click(game_env, "recycle")
    assert game_env.chain.waste_focus is None
    assert not game_env.elements["focus-recycle-button"].classList.contains("focus-button--on")


def test_switching_focus_is_free(game_env):
    c = game_env.chain
    funds = c.funds
    _click(game_env, "repair")
    _click(game_env, "reuse")
    assert c.funds == funds and c.waste_focus == "reuse"


def test_focus_helps_close_the_loop(game_env):
    m = game_env.module
    c = game_env.chain
    per_unit = m.CIRCULARITY_INVESTMENTS["recycle"]["supply_per_unit"]
    needed = int(m.PRODUCTION_TARGET / (per_unit * (1 + m.WASTE_STREAM_SPECIALIZATION_BONUS))) + 1
    c.circularity_investment["recycle"] = needed
    assert not c.is_loop_closed() or needed * per_unit >= m.PRODUCTION_TARGET
    c.set_waste_focus("recycle")
    assert c.is_loop_closed()


def test_stats_line_shows_the_focused_contribution(game_env):
    m = game_env.module
    game_env.chain.circularity_investment["recycle"] = 4
    _click(game_env, "recycle")
    text = game_env.elements["recycle-stats"].innerText
    per_unit = m.CIRCULARITY_INVESTMENTS["recycle"]["supply_per_unit"]
    assert f"supplying {4 * per_unit * (1 + m.WASTE_STREAM_SPECIALIZATION_BONUS):.0f}/cycle" in text
    assert "focus +25%" in text


def test_focus_stacks_with_challenge_mode(game_env):
    m = game_env.module
    c = game_env.chain
    c.circularity_investment["recycle"] = 4
    c.challenge_mode = True
    c.set_waste_focus("recycle")
    expected = 4 * 5.0 * 1.25 * m.CHALLENGE_MODE_SUPPLY_MULTIPLIER
    assert c.internal_circular_supply() == pytest.approx(expected)


def test_save_round_trip_and_default_omits_key(game_env):
    m = game_env.module
    assert "waste_focus" not in m.get_state()
    _click(game_env, "reuse")
    data = m.get_state()
    assert data["waste_focus"] == "reuse"
    game_env.chain.waste_focus = None
    m.load_state(data)
    assert game_env.chain.waste_focus == "reuse"


def test_load_rejects_bad_focus_values(game_env):
    m = game_env.module
    for bad in ("bogus", 1, None, ["repair"], {"a": 1}, True):
        data = m.get_state()
        data["waste_focus"] = bad
        game_env.chain.waste_focus = "repair"
        m.load_state(data)
        assert game_env.chain.waste_focus is None


def test_reset_chain_clears_focus(game_env):
    _click(game_env, "reuse")
    game_env.advance_cycle()
    game_env.elements["reset-chain-button"].dispatch("click", None)
    assert game_env.chain.waste_focus is None
