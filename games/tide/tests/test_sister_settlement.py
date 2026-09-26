"""D3: the optional sister settlement (a lower-lying twin sharing funds and tier)."""

import pytest


def _enable(game_env):
    game_env.elements["sister-enable-button"].dispatch("click", None)


def test_off_by_default_and_button_visible(game_env):
    m = game_env.module
    m.render()
    assert m.state.sister_enabled is False
    assert game_env.elements["sister-enable-button"].hidden is False
    assert game_env.elements["sister-display"].hidden is True
    assert m.state.sister_text() == ""


def test_enabling_swaps_button_for_the_readout_and_is_permanent(game_env):
    m = game_env.module
    _enable(game_env)
    assert m.state.sister_enabled is True
    assert game_env.elements["sister-enable-button"].hidden is True
    assert game_env.elements["sister-display"].hidden is False
    assert "Sister settlement" in game_env.elements["sister-display"].innerText
    assert m.state.enable_sister() is False  # cannot be added twice


def test_no_effect_on_funds_while_off(game_env):
    m = game_env.module
    baseline = m.SettlementState()
    baseline.advance_season()
    m.state.advance_season()
    assert m.state.funds == pytest.approx(baseline.funds)
    assert m.state.sister_cumulative_damage == 0.0 and m.state.sister_net_funds == 0.0


def test_sister_costs_and_earns_from_the_shared_funds(game_env):
    m = game_env.module
    plain = m.SettlementState()
    twin = m.SettlementState()
    twin.enable_sister()
    plain.advance_season()
    twin.advance_season()
    rise = twin.sea_rise_per_season()
    damage = rise * m.SISTER_EXPOSURE * (1 - twin.dampening_fraction())
    expected_net = m.SISTER_INCOME - damage * m.SISTER_FUNDS_PER_DAMAGE
    assert twin.funds - plain.funds == pytest.approx(expected_net)
    assert twin.sister_cumulative_damage == pytest.approx(damage)
    assert twin.sister_net_funds == pytest.approx(expected_net)


def test_it_shares_the_players_adaptation_tier(game_env):
    m = game_env.module
    low = m.SettlementState()
    high = m.SettlementState()
    for s in (low, high):
        s.enable_sister()
    high.capacity["adaptation"] = m.ADAPTATION_TIERS[-1]["threshold"]
    low.advance_season()
    high.advance_season()
    assert high.sister_cumulative_damage < low.sister_cumulative_damage


def test_the_sister_is_more_exposed_than_the_main_coast(game_env):
    m = game_env.module
    s = m.SettlementState()
    s.enable_sister()
    s.advance_season()
    assert s.sister_cumulative_damage > s.cumulative_damage  # 1.3x the rise, same dampening


def test_rows_flood_earlier_than_the_main_coastline(game_env):
    m = game_env.module
    s = m.SettlementState()
    s.sea_level = 0.0
    main = sum(1 for row in range(m.COASTLINE_ROWS) if s.sea_level >= m.row_flood_threshold(row))
    assert s.sister_rows_flooded() >= main
    s.sea_level = m.row_flood_threshold(m.COASTLINE_ROWS - 1) - 5.0  # just short of the main coast's first row
    assert s.sister_rows_flooded() > sum(1 for row in range(m.COASTLINE_ROWS) if s.sea_level >= m.row_flood_threshold(row))


def test_rows_flooded_is_bounded(game_env):
    m = game_env.module
    s = m.SettlementState()
    s.sea_level = 10_000.0
    assert s.sister_rows_flooded() == m.COASTLINE_ROWS


def test_display_tracks_the_seasons(game_env):
    _enable(game_env)
    before = game_env.elements["sister-display"].innerText
    game_env.advance_season()
    assert game_env.elements["sister-display"].innerText != before


def test_adaptation_investment_protects_both(game_env):
    m = game_env.module
    _enable(game_env)
    m.state.funds = 100_000
    for _ in range(40):
        m.state.invest("adaptation")
    m.state.advance_season()
    assert m.state.dampening_fraction() > 0
    assert m.state.sister_cumulative_damage < m.state.sea_rise_per_season() * m.SISTER_EXPOSURE


def test_save_round_trip_and_default_omits_key(game_env):
    m = game_env.module
    assert "sister" not in m.get_state()
    m.state.enable_sister()
    m.state.sister_cumulative_damage = 12.5
    m.state.sister_net_funds = -7.0
    data = m.get_state()
    assert data["sister"] == {"damage": 12.5, "net_funds": -7.0}
    m.state.sister_enabled = False
    m.state.sister_cumulative_damage = 0.0
    m.state.sister_net_funds = 0.0
    m.load_state(data)
    assert m.state.sister_enabled is True
    assert m.state.sister_cumulative_damage == 12.5 and m.state.sister_net_funds == -7.0


def test_load_without_the_key_turns_it_off(game_env):
    m = game_env.module
    m.state.enable_sister()
    data = m.get_state()
    del data["sister"]
    m.load_state(data)
    assert m.state.sister_enabled is False


def test_load_rejects_bad_numbers(game_env):
    m = game_env.module
    for bad in ({"damage": "x", "net_funds": None}, {"damage": -1, "net_funds": float("nan")},
                {"damage": True, "net_funds": True}, {"damage": 1e12, "net_funds": 1e12}, {}):
        data = m.get_state()
        data["sister"] = bad
        m.load_state(data)
        assert m.state.sister_enabled is True
        assert m.state.sister_cumulative_damage == 0.0 and m.state.sister_net_funds == 0.0
    for bad in ("x", [1], None, 3):
        data = m.get_state()
        data["sister"] = bad
        m.load_state(data)
        assert m.state.sister_enabled is False
