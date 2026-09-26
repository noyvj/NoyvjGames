"""I1/I7: a second, neighbouring region with a different starting profile,
plus optional support from a well-prepared main region."""


def _click(env, id_):
    env.elements[id_].dispatch("click", None)


def _open(env, funds=500.0):
    m = env.module
    m.region.round_number = m.NEIGHBOR_MIN_ROUND
    m.region.funds = funds
    m.render()
    assert m.open_neighbor() is True
    return m


def test_panel_hidden_until_the_core_loop_is_underway(game_env):
    m = game_env.module
    m.render()
    assert game_env.elements["neighbor-panel"].hidden is True
    assert m.open_neighbor() is False
    m.region.round_number = m.NEIGHBOR_MIN_ROUND
    m.render()
    assert game_env.elements["neighbor-panel"].hidden is False
    assert game_env.elements["neighbor-open-button"].hidden is False
    assert game_env.elements["neighbor-support-button"].hidden is True


def test_neighbor_starts_with_a_different_profile(game_env):
    m = _open(game_env)
    other = m.neighbor
    assert other is not m.region
    assert other.capacity["housing"] == m.NEIGHBOR_START_HOUSING
    assert other.capacity["services"] == 0
    assert other.funds < m.STARTING_FUNDS
    assert other.background_severity > 0
    assert other.arrivals_this_round() > m.region.arrivals_this_round()
    assert other.learning_active is False
    assert other.second_wave_status == "done"


def test_opening_twice_is_a_no_op(game_env):
    m = _open(game_env)
    first = m.neighbor
    assert m.open_neighbor() is False
    assert m.neighbor is first


def test_neighbor_advances_with_the_main_region(game_env):
    m = _open(game_env)
    before = m.neighbor.round_number
    game_env.advance_round()
    assert m.neighbor.round_number == before + 1
    assert m.neighbor.total_arrivals > m.NEIGHBOR_START_ARRIVALS


def test_neighbor_invests_from_its_own_funds_only(game_env):
    m = _open(game_env)
    main_funds = m.region.funds
    other_funds = m.neighbor.funds
    assert m.invest_neighbor("services") is True
    assert m.neighbor.funds == other_funds - m.INVEST_COST["services"]
    assert m.region.funds == main_funds
    m.neighbor.funds = 0.0
    assert m.invest_neighbor("housing") is False
    assert m.invest_neighbor("nonsense") is False


def test_investment_buttons_work(game_env):
    m = _open(game_env)
    m.render()
    _click(game_env, "neighbor-services-button")
    assert m.neighbor.capacity["services"] > 0
    assert game_env.elements["neighbor-services-button"].hidden is False


def test_support_needs_a_calm_region_with_a_cushion(game_env):
    m = _open(game_env, funds=10.0)
    assert m.main_region_well_prepared() is False
    assert m.support_neighbor() is False
    m.region.funds = m.NEIGHBOR_SUPPORT_AMOUNT + m.NEIGHBOR_SUPPORT_RESERVE - 1
    assert m.main_region_well_prepared() is False
    m.region.funds = m.NEIGHBOR_SUPPORT_AMOUNT + m.NEIGHBOR_SUPPORT_RESERVE
    assert m.main_region_well_prepared() is True


def test_support_moves_funds_and_is_blocked_while_the_main_region_is_strained(game_env):
    m = _open(game_env, funds=500.0)
    main, other = m.region.funds, m.neighbor.funds
    assert m.support_neighbor() is True
    assert m.region.funds == main - m.NEIGHBOR_SUPPORT_AMOUNT
    assert m.neighbor.funds == other + m.NEIGHBOR_SUPPORT_AMOUNT
    assert m.neighbor_support_sent == m.NEIGHBOR_SUPPORT_AMOUNT
    m.region.total_arrivals = 100.0  # no capacity: heavily strained
    assert m.main_region_well_prepared() is False
    assert m.support_neighbor() is False


def test_critical_neighbor_spills_extra_arrivals_into_the_main_region(game_env):
    m = _open(game_env)
    base = m.region.arrivals_this_round()
    assert m.neighbor_spillover() == 0.0
    m.neighbor.total_arrivals = 500.0
    m.neighbor.capacity["housing"] = 0.0
    assert m.neighbor.strain_fraction() >= m.STRAIN_LEVEL_THRESHOLDS[2][0]
    m.render()
    assert m.region.arrivals_this_round() == base + m.NEIGHBOR_SPILLOVER_ARRIVALS
    assert "extra people" in game_env.elements["neighbor-display"].innerText
    m.neighbor.capacity["housing"] = 1000.0
    m.render()
    assert m.region.arrivals_this_round() == base


def test_save_round_trip(game_env):
    m = _open(game_env)
    m.invest_neighbor("services")
    m.support_neighbor()
    game_env.advance_round()
    state = m.get_state()
    funds, arrivals, services = m.neighbor.funds, m.neighbor.total_arrivals, m.neighbor.capacity["services"]
    m.load_state({})
    assert m.neighbor is None and m.neighbor_support_sent == 0.0
    assert m.load_state(state) is True
    assert (m.neighbor.funds, m.neighbor.total_arrivals, m.neighbor.capacity["services"]) == (funds, arrivals, services)
    assert m.neighbor_support_sent == m.NEIGHBOR_SUPPORT_AMOUNT
    assert m.neighbor.wellbeing_score() >= 0.0


def test_default_save_has_no_neighbor_key(game_env):
    assert "neighbor" not in game_env.module.get_state()


def test_corrupt_neighbor_data_is_sanitised(game_env):
    m = game_env.module
    state = m.get_state()
    state["neighbor"] = {
        "round_number": True, "funds": "lots", "capacity": {"housing": float("nan"), "services": -5},
        "total_arrivals": float("inf"), "integrated_population": 10 ** 9, "strain_count": -3,
        "strain_sum": 10 ** 6, "support_sent": [],
    }
    assert m.load_state(state) is True
    other = m.neighbor
    assert other.round_number == 1
    assert other.funds == m.NEIGHBOR_START_FUNDS
    assert other.capacity["housing"] == m.NEIGHBOR_START_HOUSING and other.capacity["services"] == 0.0
    assert other.integrated_population <= other.total_arrivals
    assert other._strain_sum <= other._strain_count
    game_env.advance_round()
    m.load_state({"neighbor": "nope"})
    assert m.neighbor is None
