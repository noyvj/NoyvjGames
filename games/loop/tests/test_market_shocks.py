"""GH-3 / FY-37: deterministic, announced market shocks (opt-in)."""

import json

import pytest


def shocks_on(env):
    env.elements["market-shocks-button"].dispatch("click", None)
    assert env.chain.market_shocks is True


def go_to_cycle(env, cycle):
    env.chain.cycle_number = cycle
    env.module.render()


# ------------------------------------------------------------------ the schedule itself
def test_the_schedule_is_fixed_and_repeats_every_period(game_env):
    f = game_env.module.shock_for_cycle
    kinds = {c: (f(c) or {}).get("kind") for c in range(1, 17)}
    assert kinds[5] == "price_spike"
    assert [kinds[c] for c in (9, 10, 11)] == ["port_strike"] * 3
    assert kinds[13] == "demand_surge"
    assert [c for c, k in kinds.items() if k] == [5, 9, 10, 11, 13]
    # the next block is the same shape, 15 cycles later
    assert [bool(f(c)) for c in range(16, 31)] == [bool(f(c)) for c in range(1, 16)]
    assert f(0) is None and f(-3) is None


def test_the_schedule_has_no_randomness(game_env):
    f = game_env.module.shock_for_cycle
    assert [f(c) for c in range(1, 60)] == [f(c) for c in range(1, 60)]


def test_the_strike_hits_a_different_partner_each_block(game_env):
    f = game_env.module.shock_for_cycle
    partners = [f(9 + 15 * block)["partner"] for block in range(4)]
    assert partners == ["trade", "regional", "overseas", "trade"]


def test_strike_steps_and_span(game_env):
    f = game_env.module.shock_for_cycle
    assert [f(c)["step"] for c in (9, 10, 11)] == [1, 2, 3]
    assert all(f(c)["start"] == 9 and f(c)["length"] == 3 for c in (9, 10, 11))


# ------------------------------------------------------------------ off by default
def test_the_mode_is_off_by_default_and_changes_nothing(game_env):
    chain = game_env.chain
    assert chain.market_shocks is False
    go_to_cycle(game_env, 5)
    assert chain.active_shock() is None and chain.next_shock() is None
    assert chain.price_multiplier() == chain.extraction_cost_multiplier()
    assert chain.material_need() == game_env.module.PRODUCTION_TARGET
    assert game_env.elements["shock-banner"].hidden is True
    assert "Off." in game_env.elements["shock-status"].innerText
    assert "market_shocks" not in game_env.module.get_state()


def test_the_switch_toggles_the_mode(game_env):
    shocks_on(game_env)
    assert game_env.elements["market-shocks-button"].innerText == "Market shocks: on"
    assert game_env.elements["market-shocks-button"].attributes["aria-pressed"] == "true"
    game_env.elements["market-shocks-button"].dispatch("click", None)
    assert game_env.chain.market_shocks is False


# ------------------------------------------------------------------ the early warning
def test_a_shock_is_announced_one_cycle_early(game_env):
    shocks_on(game_env)
    go_to_cycle(game_env, 4)
    banner = game_env.elements["shock-banner"]
    assert banner.hidden is False
    assert "Heads-up for next cycle: Price spike" in banner.innerText
    assert "Market shock now" not in banner.innerText
    go_to_cycle(game_env, 5)
    assert "Market shock now: Price spike" in banner.innerText
    go_to_cycle(game_env, 6)
    assert banner.hidden is True


def test_a_strike_is_announced_once_not_on_every_strike_cycle(game_env):
    shocks_on(game_env)
    go_to_cycle(game_env, 8)
    assert "Port strike at the Trade Link" in game_env.elements["shock-banner"].innerText
    go_to_cycle(game_env, 9)
    text = game_env.elements["shock-banner"].innerText
    assert "day 1 of 3" in text and "Heads-up" not in text
    go_to_cycle(game_env, 10)
    assert "day 2 of 3" in game_env.elements["shock-banner"].innerText
    assert game_env.chain.next_shock() is None


def test_the_surge_is_announced_too(game_env):
    shocks_on(game_env)
    go_to_cycle(game_env, 12)
    assert "Demand surge" in game_env.elements["shock-banner"].innerText


# ------------------------------------------------------------------ the effects
def test_a_price_spike_raises_what_extraction_costs_for_that_cycle_only(game_env):
    chain = game_env.chain
    shocks_on(game_env)
    go_to_cycle(game_env, 5)
    funds_before = chain.funds
    chain.advance_cycle()
    # 50 units at base cost 2.0 x spike 1.5, revenue 250
    assert chain.funds == pytest.approx(funds_before + 250 - 50 * 2.0 * 1.5)
    funds_before = chain.funds
    expected_cost = 50 * 2.0 * chain.extraction_cost_multiplier()  # cycle 6: no shock, damage only
    chain.advance_cycle()
    assert chain.funds == pytest.approx(funds_before + 250 - expected_cost)


def test_the_extraction_price_line_names_the_spike(game_env):
    shocks_on(game_env)
    go_to_cycle(game_env, 5)
    assert "price spike 1.5" in game_env.elements["cost-equation-display"].innerText
    go_to_cycle(game_env, 6)
    assert "price spike" not in game_env.elements["cost-equation-display"].innerText


def test_a_demand_surge_raises_the_material_the_chain_needs(game_env):
    chain = game_env.chain
    shocks_on(game_env)
    go_to_cycle(game_env, 13)
    assert chain.material_need() == pytest.approx(60.0)
    assert chain.new_extraction_needed() == pytest.approx(60.0)
    assert chain.circular_fraction_this_cycle() == 0.0  # never negative
    chain.advance_cycle()
    assert chain.total_extracted == pytest.approx(60.0)
    assert chain.lifetime_circular_fraction() == 0.0  # clamped, never negative


def test_a_chain_with_spare_supply_shrugs_off_a_surge(game_env):
    chain = game_env.chain
    chain.funds = 5000.0
    for _ in range(13):
        game_env.invest_circularity("recycle")  # 65 units of supply
    shocks_on(game_env)
    go_to_cycle(game_env, 13)
    assert chain.new_extraction_needed() == 0.0
    assert chain.is_loop_closed()


def test_a_port_strike_cuts_only_the_struck_partners_imports(game_env):
    chain = game_env.chain
    chain.funds = 5000.0
    for _ in range(2):
        game_env.invest_trade_link()
        game_env.invest_regional_trade()
    full = chain.imported_supply()
    shocks_on(game_env)
    go_to_cycle(game_env, 9)  # the first block strikes the Trade Link
    assert chain.blocked_partner() == "trade"
    assert chain.imported_supply() == pytest.approx(full - 2 * game_env.module.IMPORT_SUPPLY_PER_UNIT)
    go_to_cycle(game_env, 12)
    assert chain.blocked_partner() is None
    assert chain.imported_supply() == pytest.approx(full)


def test_the_text_and_visual_maps_show_the_strike(game_env):
    chain = game_env.chain
    chain.funds = 5000.0
    game_env.invest_trade_link()
    shocks_on(game_env)
    go_to_cycle(game_env, 9)
    text = game_env.elements["network-map-display"].innerText
    assert "Trade Link          in +0  (port strike: shut)" in text
    flows = {key: units for key, _l, _i, _o, units, _c in game_env.module.trade_partner_flows()}
    assert flows["link"] == 0.0
    assert sum(flows.values()) == pytest.approx(chain.imported_supply())


def test_flows_still_sum_to_imports_on_a_normal_cycle(game_env):
    chain = game_env.chain
    chain.funds = 5000.0
    game_env.invest_trade_link()
    game_env.invest_overseas_trade()
    total = sum(units for *_x, units, _c in game_env.module.trade_partner_flows())
    assert total == pytest.approx(chain.imported_supply())


# ------------------------------------------------------------------ the achievement
def test_shock_absorber_counts_closed_cycles_that_landed_on_a_shock(game_env):
    m = game_env.module
    chain = game_env.chain
    chain.funds = 5000.0
    for _ in range(14):
        game_env.invest_circularity("recycle")  # 70 units: closed even in a surge
    shocks_on(game_env)
    go_to_cycle(game_env, 5)
    chain.advance_cycle()  # price spike, closed
    assert chain.shocks_shrugged == 1
    chain.advance_cycle()  # cycle 6, no shock
    assert chain.shocks_shrugged == 1
    go_to_cycle(game_env, 9)
    for _ in range(3):
        chain.advance_cycle()
    go_to_cycle(game_env, 13)
    chain.advance_cycle()
    assert chain.shocks_shrugged == 5
    assert "shock_absorber" in m.achievement_ids_earned()


def test_an_unclosed_cycle_on_a_shock_does_not_count(game_env):
    chain = game_env.chain
    shocks_on(game_env)
    go_to_cycle(game_env, 5)
    chain.advance_cycle()
    assert chain.shocks_shrugged == 0


def test_shock_absorber_is_in_the_catalog_with_a_story_chapter():
    from pathlib import Path
    here = Path(__file__).resolve().parent.parent
    ids = [a["id"] for a in json.loads((here / "achievements.json").read_text())["achievements"]]
    assert "shock_absorber" in ids
    chapters = {c["id"] for c in json.loads((here / "story.json").read_text())["chapters"]}
    assert "shock_absorber" in chapters


# ------------------------------------------------------------------ saves
def test_saves_write_the_keys_only_when_they_matter(game_env):
    m = game_env.module
    state = m.get_state()
    assert "market_shocks" not in state and "shocks_shrugged" not in state
    shocks_on(game_env)
    game_env.chain.shocks_shrugged = 3
    state = m.get_state()
    assert state["market_shocks"] is True and state["shocks_shrugged"] == 3


def test_round_trip(game_env):
    m = game_env.module
    shocks_on(game_env)
    game_env.chain.shocks_shrugged = 4
    saved = json.loads(json.dumps(m.get_state()))
    game_env.chain.market_shocks = False
    game_env.chain.shocks_shrugged = 0
    m.load_state(saved)
    assert game_env.chain.market_shocks is True and game_env.chain.shocks_shrugged == 4


@pytest.mark.parametrize("bad", ["yes", None, [], -2, 2.5, True, 10**9])
def test_bad_saved_values_load_as_defaults(game_env, bad):
    m = game_env.module
    state = m.get_state()
    state["market_shocks"] = bad
    state["shocks_shrugged"] = bad
    m.load_state(state)
    assert game_env.chain.market_shocks is (bad is True)
    assert game_env.chain.shocks_shrugged == 0


def test_old_saves_load_with_the_mode_off(game_env):
    m = game_env.module
    state = m.get_state()
    for key in ("market_shocks", "shocks_shrugged"):
        state.pop(key, None)
    m.load_state(state)
    assert game_env.chain.market_shocks is False and game_env.chain.shocks_shrugged == 0


def test_a_rewind_takes_the_mode_back_with_the_chain(game_env):
    chain = game_env.chain
    shocks_on(game_env)
    go_to_cycle(game_env, 5)
    chain.advance_cycle()
    assert chain.rewind()
    assert chain.market_shocks is True and chain.cycle_number == 5
