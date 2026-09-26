"""F1: a satellite farm with its own coupling ratio, offset by the main
farm's surplus decoupling."""


def _click(env, id_):
    env.elements[id_].dispatch("click", None)


def _ready(env, funds=1000.0):
    m = env.module
    env.farm.herd_size = m.SATELLITE_MIN_MAIN_HERD
    env.farm.funds = funds
    m.render()
    return m


def test_hidden_until_the_main_farm_is_established(game_env):
    m = game_env.module
    m.render()
    assert game_env.elements["satellite-panel"].hidden is True
    assert game_env.farm.open_satellite() is False
    _ready(game_env)
    assert game_env.elements["satellite-panel"].hidden is False
    assert game_env.elements["satellite-open-button"].hidden is False
    assert game_env.elements["satellite-grow-button"].hidden is True


def test_opening_costs_funds_and_only_once(game_env):
    m = _ready(game_env)
    before = game_env.farm.funds
    assert game_env.farm.open_satellite() is True
    assert game_env.farm.funds == before - m.SATELLITE_OPEN_COST
    assert game_env.farm.open_satellite() is False
    assert game_env.farm.funds == before - m.SATELLITE_OPEN_COST


def test_cannot_open_without_funds(game_env):
    _ready(game_env, funds=1.0)
    assert game_env.farm.open_satellite() is False
    assert game_env.farm.satellite_open is False


def test_growing_needs_it_open_and_stops_at_the_size_limit(game_env):
    m = _ready(game_env)
    farm = game_env.farm
    assert farm.grow_satellite() is False
    farm.open_satellite()
    farm.funds = 10 ** 6
    for _ in range(m.SATELLITE_MAX_SIZE):
        assert farm.grow_satellite() is True
    assert farm.grow_satellite() is False
    assert farm.satellite_size == m.SATELLITE_MAX_SIZE


def test_retrofits_lower_its_own_ratio_down_to_a_floor(game_env):
    m = _ready(game_env)
    farm = game_env.farm
    farm.open_satellite()
    farm.funds = 10 ** 6
    assert farm.satellite_own_ratio() == m.SATELLITE_BASE_RATIO
    farm.retrofit_satellite()
    assert farm.satellite_own_ratio() < m.SATELLITE_BASE_RATIO
    for _ in range(50):
        farm.retrofit_satellite()
    assert farm.satellite_retrofits == m.SATELLITE_MAX_RETROFITS
    assert farm.satellite_own_ratio() >= m.MIN_SATELLITE_RATIO


def test_main_farm_surplus_decoupling_offsets_the_satellite(game_env):
    m = _ready(game_env)
    farm = game_env.farm
    farm.open_satellite()
    assert farm.satellite_offset_fraction() == 0.0
    assert farm.satellite_coupling_ratio() == m.SATELLITE_BASE_RATIO
    farm.decoupling_investment["capture"] = 8  # main ratio 1.0 -> 0.2, decoupled 0.8
    offset = farm.satellite_offset_fraction()
    assert 0 < offset <= m.SATELLITE_MAX_OFFSET
    assert farm.satellite_coupling_ratio() < m.SATELLITE_BASE_RATIO
    farm.decoupling_investment["capture"] = 100
    assert farm.satellite_offset_fraction() == m.SATELLITE_MAX_OFFSET


def test_satellite_adds_income_and_methane_to_the_round(game_env):
    m = _ready(game_env)
    farm = game_env.farm
    farm.open_satellite()
    farm.funds = 10 ** 6
    farm.grow_satellite()
    farm.grow_satellite()
    base_methane = farm.herd_size * farm.coupling_ratio()
    assert farm.methane_this_round() == base_methane + 2 * farm.satellite_coupling_ratio()
    funds_before = farm.funds
    farm.advance_round()
    assert farm.funds > funds_before + farm.herd_size * m.HERD_INCOME_PER_UNIT * 0.9  # main income alone
    assert farm.counterfactual_methane == farm.herd_size * m.BASE_COUPLING_RATIO + 2 * m.SATELLITE_BASE_RATIO


def test_regional_cap_counts_the_satellite(game_env):
    m = _ready(game_env)
    farm = game_env.farm
    farm.open_satellite()
    farm.funds = 10 ** 6
    farm.regional_cap_enabled = True
    farm.herd_size = int(m.REGIONAL_CAP / farm.coupling_ratio())
    assert farm.cap_blocks_growth(satellite=1) is True
    assert farm.grow_satellite() is False


def test_buttons_drive_the_farm(game_env):
    m = _ready(game_env)
    _click(game_env, "satellite-open-button")
    assert game_env.farm.satellite_open is True
    assert game_env.elements["satellite-grow-button"].hidden is False
    _click(game_env, "satellite-grow-button")
    _click(game_env, "satellite-retrofit-button")
    assert game_env.farm.satellite_size == 1 and game_env.farm.satellite_retrofits == 1
    assert "1 of" in game_env.elements["satellite-display"].innerText
    assert str(m.SATELLITE_MAX_SIZE) in game_env.elements["satellite-display"].innerText


def test_save_round_trip_and_default_saves_unchanged(game_env):
    m = _ready(game_env)
    assert not [k for k in m.get_state() if k.startswith("satellite")]
    farm = game_env.farm
    farm.open_satellite()
    farm.funds = 10 ** 6
    farm.grow_satellite()
    farm.retrofit_satellite()
    state = m.get_state()
    m.load_state({})
    assert m.farm.satellite_open is False
    m.load_state(state)
    assert (m.farm.satellite_open, m.farm.satellite_size, m.farm.satellite_retrofits) == (True, 1, 1)


def test_corrupt_satellite_fields_are_clamped(game_env):
    m = game_env.module
    m.load_state({"satellite_open": True, "satellite_size": 10 ** 9, "satellite_retrofits": True})
    assert m.farm.satellite_size == m.SATELLITE_MAX_SIZE
    assert m.farm.satellite_retrofits == 0
    m.load_state({"satellite_open": "yes", "satellite_size": 5})
    assert m.farm.satellite_open is False and m.farm.satellite_size == 0
    m.load_state({"satellite_open": True, "satellite_size": float("nan"), "satellite_retrofits": -3})
    assert m.farm.satellite_size == 0 and m.farm.satellite_retrofits == 0


def test_a_handover_starts_a_new_farm_without_the_satellite(game_env):
    m = _ready(game_env)
    game_env.farm.open_satellite()
    game_env.farm.certified = True
    m.hand_over_farm()
    assert m.farm.satellite_open is False and m.farm.satellite_size == 0
