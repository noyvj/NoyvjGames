"""H17: consumer behavior (a demand-side culture campaign)."""

import pytest


def _click(env):
    env.elements["culture-invest-button"].dispatch("click", None)


def test_starts_at_zero_and_matches_the_production_target(game_env):
    m = game_env.module
    assert game_env.chain.culture_level == 0
    assert game_env.chain.material_need() == m.PRODUCTION_TARGET


def test_investing_spends_funds_and_lowers_need(game_env):
    m = game_env.module
    game_env.chain.funds = 200
    _click(game_env)
    assert game_env.chain.culture_level == 1
    assert game_env.chain.funds == 200 - m.CULTURE_BASE_COST
    assert game_env.chain.material_need() == pytest.approx(m.PRODUCTION_TARGET * (1 - m.CULTURE_DEMAND_REDUCTION))


def test_cost_grows_and_caps_at_the_max_level(game_env):
    m = game_env.module
    c = game_env.chain
    c.funds = 100_000
    costs = []
    for _ in range(m.CULTURE_MAX_LEVEL):
        costs.append(c.culture_cost())
        assert c.invest_culture()
    assert costs == [m.CULTURE_BASE_COST * n for n in range(1, m.CULTURE_MAX_LEVEL + 1)]
    assert c.invest_culture() is False and c.culture_level == m.CULTURE_MAX_LEVEL
    assert c.material_need() > 0


def test_needs_funds(game_env):
    game_env.chain.funds = 1
    _click(game_env)
    assert game_env.chain.culture_level == 0


def test_demand_reduction_shrinks_extraction_without_any_supply(game_env):
    m = game_env.module
    c = game_env.chain
    assert c.new_extraction_needed() == m.PRODUCTION_TARGET
    c.culture_level = 3
    assert c.new_extraction_needed() == pytest.approx(m.PRODUCTION_TARGET * (1 - 3 * m.CULTURE_DEMAND_REDUCTION))


def test_supply_and_demand_combine(game_env):
    m = game_env.module
    c = game_env.chain
    c.circularity_investment["recycle"] = 6  # 30 units of supply
    before = c.new_extraction_needed()
    c.culture_level = 2
    assert c.new_extraction_needed() == pytest.approx(before - m.PRODUCTION_TARGET * 2 * m.CULTURE_DEMAND_REDUCTION)


def test_demand_side_helps_close_the_loop_with_less_supply(game_env):
    m = game_env.module
    c = game_env.chain
    c.circularity_investment["recycle"] = int(m.PRODUCTION_TARGET * 0.8 / 5)  # just short
    assert not c.is_loop_closed()
    c.culture_level = m.CULTURE_MAX_LEVEL
    assert c.is_loop_closed()


def test_exportable_surplus_uses_the_reduced_need(game_env):
    m = game_env.module
    c = game_env.chain
    c.circularity_investment["recycle"] = 10  # 50 units
    assert c.exportable_surplus() == 0
    c.culture_level = 2
    assert c.exportable_surplus() == pytest.approx(m.PRODUCTION_TARGET * 2 * m.CULTURE_DEMAND_REDUCTION)


def test_revenue_is_unchanged_by_the_campaign(game_env):
    m = game_env.module
    c = game_env.chain
    c.culture_level = 5
    c.funds = 0
    game_env.advance_cycle()
    expected_extraction_cost = c.material_need() * m.EXTRACTION_COST_PER_UNIT
    assert c.funds == pytest.approx(m.PRODUCTION_TARGET * m.SALE_PRICE_PER_UNIT - expected_extraction_cost)


def test_display_updates(game_env):
    game_env.chain.funds = 500
    _click(game_env)
    assert game_env.elements["culture-count"].innerText == "1"
    assert "48 of 50" in game_env.elements["culture-stats"].innerText
    assert "Culture campaign (" in game_env.elements["culture-invest-button"].innerText


def test_max_level_disables_the_button(game_env):
    m = game_env.module
    game_env.chain.culture_level = m.CULTURE_MAX_LEVEL
    m.render()
    button = game_env.elements["culture-invest-button"]
    assert button.disabled is True and "max" in button.innerText


def test_save_round_trip_and_default_omits_key(game_env):
    m = game_env.module
    assert "culture_level" not in m.get_state()
    game_env.chain.culture_level = 3
    data = m.get_state()
    assert data["culture_level"] == 3
    game_env.chain.culture_level = 0
    m.load_state(data)
    assert game_env.chain.culture_level == 3


def test_load_rejects_bad_values(game_env):
    m = game_env.module
    for bad in (-1, 99, "2", 2.5, None, True, [1]):
        data = m.get_state()
        data["culture_level"] = bad
        game_env.chain.culture_level = 4
        m.load_state(data)
        assert game_env.chain.culture_level == 0


def test_reset_chain_clears_it(game_env):
    game_env.chain.culture_level = 2
    game_env.advance_cycle()
    game_env.elements["reset-chain-button"].dispatch("click", None)
    assert game_env.chain.culture_level == 0
