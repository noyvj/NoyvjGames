"""H3: supply chain redesign (a late-game layer that opens once the loop has closed)."""

import pytest


def _unlock(game_env):
    game_env.chain.first_loop_closed_cycle = 3


def _click(env, measure):
    env.elements[f"redesign-{measure}-button"].dispatch("click", None)


def test_locked_until_the_loop_has_closed(game_env):
    m = game_env.module
    game_env.chain.funds = 10_000
    assert game_env.chain.redesign_unlocked() is False
    assert game_env.chain.redesign("repair") is False
    m.render()
    button = game_env.elements["redesign-repair-button"]
    assert button.disabled is True and "unlocks once the loop closes" in button.innerText


def test_unlocks_after_first_close_and_charges_funds(game_env):
    m = game_env.module
    _unlock(game_env)
    game_env.chain.funds = 500
    assert game_env.chain.redesign("reuse") is True
    assert game_env.chain.redesign_level["reuse"] == 1
    assert game_env.chain.funds == 500 - m.REDESIGN_BASE_COST


def test_cost_grows_per_level_and_caps(game_env):
    m = game_env.module
    _unlock(game_env)
    c = game_env.chain
    c.funds = 100_000
    costs = []
    for _ in range(m.REDESIGN_MAX_LEVEL):
        costs.append(c.redesign_cost("repair"))
        assert c.redesign("repair")
    assert costs == [m.REDESIGN_BASE_COST * n for n in (1, 2, 3)]
    assert c.redesign("repair") is False and c.redesign_level["repair"] == m.REDESIGN_MAX_LEVEL


def test_needs_enough_funds(game_env):
    m = game_env.module
    _unlock(game_env)
    game_env.chain.funds = m.REDESIGN_BASE_COST - 1
    assert game_env.chain.redesign("recycle") is False
    assert game_env.chain.redesign_level["recycle"] == 0


def test_unknown_measure_rejected(game_env):
    _unlock(game_env)
    game_env.chain.funds = 10_000
    for bad in ("bogus", "", None):
        assert game_env.chain.redesign(bad) is False


def test_bonus_raises_only_that_measures_supply(game_env):
    m = game_env.module
    c = game_env.chain
    c.circularity_investment.update({"repair": 4, "reuse": 4, "recycle": 4})
    base = c.internal_circular_supply()
    c.redesign_level["reuse"] = 2
    extra = 4 * m.CIRCULARITY_INVESTMENTS["reuse"]["supply_per_unit"] * 2 * m.REDESIGN_SUPPLY_BONUS
    assert c.internal_circular_supply() == pytest.approx(base + extra)


def test_stacks_additively_with_the_h9_focus(game_env):
    m = game_env.module
    c = game_env.chain
    c.redesign_level["recycle"] = 3
    c.set_waste_focus("recycle")
    assert c.measure_multiplier("recycle") == pytest.approx(1 + m.WASTE_STREAM_SPECIALIZATION_BONUS + 3 * m.REDESIGN_SUPPLY_BONUS)


def test_button_click_buys_a_level_and_updates_the_display(game_env):
    _unlock(game_env)
    game_env.chain.funds = 1000
    game_env.chain.circularity_investment["repair"] = 5
    _click(game_env, "repair")
    assert game_env.chain.redesign_level["repair"] == 1
    assert "redesign +5%" in game_env.elements["repair-stats"].innerText
    assert "Redesign (" in game_env.elements["redesign-repair-button"].innerText


def test_max_level_button_state(game_env):
    m = game_env.module
    _unlock(game_env)
    game_env.chain.redesign_level["repair"] = m.REDESIGN_MAX_LEVEL
    m.render()
    button = game_env.elements["redesign-repair-button"]
    assert button.disabled is True and "max" in button.innerText


def test_unaffordable_button_is_disabled(game_env):
    _unlock(game_env)
    game_env.chain.funds = 1
    game_env.module.render()
    assert game_env.elements["redesign-reuse-button"].disabled is True


def test_save_round_trip_and_default_omits_key(game_env):
    m = game_env.module
    assert "redesign_level" not in m.get_state()
    game_env.chain.redesign_level.update({"repair": 2, "recycle": 1})
    data = m.get_state()
    assert data["redesign_level"] == {"repair": 2, "reuse": 0, "recycle": 1}
    game_env.chain.redesign_level = {k: 0 for k in game_env.chain.redesign_level}
    m.load_state(data)
    assert game_env.chain.redesign_level == {"repair": 2, "reuse": 0, "recycle": 1}


def test_load_rejects_bad_values(game_env):
    m = game_env.module
    data = m.get_state()
    data["redesign_level"] = {"repair": 99, "reuse": -1, "recycle": "2", "fake": 1}
    m.load_state(data)
    assert game_env.chain.redesign_level == {"repair": 0, "reuse": 0, "recycle": 0}
    for bad in ("x", [1], None, 5):
        data["redesign_level"] = bad
        m.load_state(data)
        assert game_env.chain.redesign_level == {"repair": 0, "reuse": 0, "recycle": 0}


def test_reset_chain_clears_redesigns(game_env):
    _unlock(game_env)
    game_env.chain.redesign_level["repair"] = 2
    game_env.advance_cycle()
    game_env.elements["reset-chain-button"].dispatch("click", None)
    assert game_env.chain.redesign_level == {"repair": 0, "reuse": 0, "recycle": 0}
