"""Round-3 Herd items: F23 poultry, F5 genetics, F13 supply chain, F15 welfare,
F9/F3 variation, F17 vignettes, F19 regional cap, F27 policy advisor, F29 biogas."""


def _certify(farm):
    farm.certified = True


# ---- F23 poultry ----
def test_poultry_locked_until_certified(game_env):
    farm = game_env.farm
    farm.funds = 500
    assert farm.grow_poultry() is False and farm.invest_poultry("litter") is False
    assert game_env.elements["poultry-panel"].hidden is True
    _certify(farm)
    game_env.module.render()
    assert game_env.elements["poultry-panel"].hidden is False
    assert farm.grow_poultry() is True and farm.poultry_size == 1


def test_poultry_own_coupling_curve_and_levers(game_env):
    farm, m = game_env.farm, game_env.module
    _certify(farm)
    farm.funds = 500
    assert farm.poultry_coupling_ratio() == m.POULTRY_BASE_RATIO < m.BASE_COUPLING_RATIO
    farm.invest_poultry("litter")
    farm.invest_poultry("biofilter")
    assert abs(farm.poultry_coupling_ratio() - (m.POULTRY_BASE_RATIO - 0.09)) < 1e-9
    for _ in range(20):
        farm.invest_poultry("biofilter")
        farm.funds = 500
    assert farm.poultry_coupling_ratio() == m.MIN_POULTRY_RATIO
    # cattle ratio is untouched by poultry levers
    assert farm.coupling_ratio() == m.BASE_COUPLING_RATIO


def test_poultry_adds_methane_income_and_upkeep(game_env):
    farm, m = game_env.farm, game_env.module
    _certify(farm)
    farm.poultry_size = 10
    farm.advance_round()
    assert abs(farm.methane - 10 * m.POULTRY_BASE_RATIO) < 1e-9
    assert abs(farm.funds - (m.STARTING_FUNDS + 10 * (m.POULTRY_INCOME_PER_UNIT - m.POULTRY_UPKEEP_PER_UNIT))) < 1e-9
    assert abs(farm.counterfactual_methane - 10 * m.POULTRY_BASE_RATIO) < 1e-9


def test_poultry_buttons_wired(game_env):
    farm = game_env.farm
    _certify(farm)
    farm.funds = 500
    game_env.module.render()
    game_env.elements["poultry-grow-button"].dispatch("click", None)
    game_env.elements["litter-invest-button"].dispatch("click", None)
    assert farm.poultry_size == 1 and farm.poultry_investment["litter"] == 1


# ---- F5 genetics ----
def test_genetics_slow_burn(game_env):
    farm, m = game_env.farm, game_env.module
    farm.funds = 100
    assert farm.invest_genetics()
    assert farm.coupling_ratio() == m.BASE_COUPLING_RATIO
    for _ in range(m.GENETICS_MATURE_ROUNDS):
        farm.advance_round()
    assert farm.genetics_active == 1 and farm.genetics_pending == []
    assert abs(farm.coupling_ratio() - (1 - m.GENETICS_RATIO_REDUCTION)) < 1e-9


# ---- F13 supply chain ----
def test_supply_chain_boosts_income_and_caps(game_env):
    farm, m = game_env.farm, game_env.module
    farm.funds = 1000
    farm.herd_size = 10
    for _ in range(10):
        farm.invest_supply_chain()
    assert farm.supply_chain_investment == m.SUPPLY_CHAIN_MAX_UNITS
    before = farm.funds
    farm.advance_round()
    assert abs((farm.funds - before) - 50 * (1 + 5 * m.SUPPLY_CHAIN_BONUS_PER_UNIT)) < 1e-9


# ---- F15 welfare ----
def test_welfare_rises_with_feed_and_lifts_income(game_env):
    farm = game_env.farm
    assert farm.welfare() == 50 and farm.welfare_multiplier() == 1.0
    farm.decoupling_investment["feed"] = 4
    assert farm.welfare() == 70 and farm.welfare_multiplier() > 1.0
    farm.decoupling_investment["feed"] = 100
    assert farm.welfare() == 100 and abs(farm.welfare_multiplier() - 1.1) < 1e-9
    game_env.module.render()
    assert "Herd welfare: 100/100" in game_env.elements["welfare-display"].innerText


# ---- F9 / F3 variation ----
def test_variation_off_by_default_and_deterministic_when_on(game_env):
    farm, m = game_env.farm, game_env.module
    assert farm.season_modifier() == 0.0
    farm.variation_enabled = True
    assert farm.season_modifier(3) == m.season_for_round(3)[1]
    assert farm.season_modifier(3) == farm.season_modifier(3)
    mods = {farm.season_modifier(r) for r in range(1, 20)}
    assert len(mods) > 1 and all(-0.1 <= x <= 0.1 for x in mods)


def test_variation_changes_income_and_demand_surge_boosts_plant_income(game_env):
    farm, m = game_env.farm, game_env.module
    farm.herd_size = 10
    farm.variation_enabled = True
    r = next(r for r in range(1, 30) if farm.season_modifier(r) != 0)
    farm.round_number = r
    before = farm.funds
    farm.advance_round()
    assert abs((farm.funds - before) - 50 * (1 + farm.season_modifier(r))) < 1e-9
    surge = next(r for r in range(1, 30) if m.demand_surge_active(r))
    assert farm.plant_income_multiplier(surge) == m.DEMAND_SURGE_PLANT_INCOME_MULTIPLIER
    farm.variation_enabled = False
    assert farm.plant_income_multiplier(surge) == m.PLANT_BASED_INCOME_MULTIPLIER


# ---- F17 vignettes ----
def test_vignette_reacts_to_ratio_bands(game_env):
    farm, m = game_env.farm, game_env.module
    assert m.farm_vignette() in ["\U0001F69C " + v for v in m.VIGNETTES["coupled"]]
    farm.decoupling_investment["capture"] = 4
    assert m.farm_vignette() in ["\U0001F69C " + v for v in m.VIGNETTES["improving"]]
    farm.decoupling_investment["capture"] = 9
    farm.plant_pivot_investment = 12
    assert m.farm_vignette() in ["\U0001F69C " + v for v in m.VIGNETTES["clean"]]


# ---- F19 regional cap ----
def test_regional_cap_blocks_growth_until_decoupled(game_env):
    farm, m = game_env.farm, game_env.module
    farm.funds = 100000
    farm.regional_cap_enabled = True
    while farm.grow_herd():
        pass
    assert farm.herd_size == int(m.REGIONAL_CAP)
    farm.invest_decoupling("capture")
    assert farm.grow_herd() is True
    farm.regional_cap_enabled = False
    assert farm.cap_blocks_growth(herd=1000) is False


def test_cap_checkbox_toggles_state(game_env):
    game_env.elements["cap-checkbox"].checked = True
    game_env.elements["cap-checkbox"].dispatch("click", None)
    assert game_env.farm.regional_cap_enabled is True


# ---- F27 policy advisor ----
def test_policy_offer_every_interval_and_choices(game_env):
    farm, m = game_env.farm, game_env.module
    for _ in range(m.POLICY_EVENT_INTERVAL - 2):
        farm.advance_round()
    assert farm.policy_offer_pending is False
    farm.advance_round()
    assert farm.policy_offer_pending is True
    game_env.module.render()
    assert game_env.elements["policy-panel"].hidden is False
    funds = farm.funds
    game_env.elements["policy-cash-button"].dispatch("click", None)
    assert farm.funds == funds + m.POLICY_CASH_BONUS and farm.policy_offer_pending is False
    assert farm.choose_policy("cash") is False


def test_policy_subsidy_discounts_and_expires(game_env):
    farm, m = game_env.farm, game_env.module
    farm.policy_offer_pending = True
    farm.choose_policy("subsidy")
    assert abs(farm.decoupling_cost("capture") - 20 * 0.7) < 1e-9
    farm.funds = 100
    farm.invest_decoupling("capture")
    assert abs(farm.funds - (100 - 14)) < 1e-9
    for _ in range(m.POLICY_SUBSIDY_ROUNDS):
        farm.advance_round()
    assert farm.decoupling_cost("capture") == 20


# ---- F29 biogas ----
def test_biogas_sold_only_from_surplus_capture(game_env):
    farm, m = game_env.farm, game_env.module
    farm.herd_size = 10
    farm.decoupling_investment["capture"] = m.CAPTURE_SELF_USE_UNITS
    assert farm.biogas_sales() == 0
    farm.decoupling_investment["capture"] = m.CAPTURE_SELF_USE_UNITS + 4
    assert abs(farm.biogas_sales() - 10 * 4 * m.BIOGAS_SALE_PER_UNIT) < 1e-9
    before = farm.funds
    farm.advance_round()
    assert abs((farm.funds - before) - (50 + farm.biogas_sales())) < 1e-9


# ---- save round trip / defaults ----
def test_new_fields_round_trip_and_old_saves_default(game_env):
    farm, m = game_env.farm, game_env.module
    farm.certified = True
    farm.poultry_size = 3
    farm.poultry_investment["litter"] = 2
    farm.genetics_active, farm.genetics_pending = 1, [2]
    farm.supply_chain_investment = 2
    farm.variation_enabled = farm.regional_cap_enabled = True
    farm.policy_offer_pending = True
    farm.subsidy_rounds_left = 3
    data = m.get_state()
    farm.__init__()
    m.load_state(data)
    assert (farm.poultry_size, farm.poultry_investment["litter"], farm.genetics_active) == (3, 2, 1)
    assert farm.genetics_pending == [2] and farm.supply_chain_investment == 2
    assert farm.variation_enabled and farm.regional_cap_enabled and farm.policy_offer_pending
    assert farm.subsidy_rounds_left == 3
    m.load_state({"round_number": 4})
    assert farm.poultry_size == 0 and farm.genetics_pending == [] and not farm.variation_enabled


def test_load_state_rejects_garbage_in_new_fields(game_env):
    farm, m = game_env.farm, game_env.module
    m.load_state({
        "poultry_size": "lots", "poultry_investment": [1], "genetics_pending": "x",
        "supply_chain_investment": 999, "variation_enabled": "yes",
        "subsidy_rounds_left": float("nan"), "genetics_active": -5,
    })
    assert farm.poultry_size == 0 and farm.genetics_pending == []
    assert farm.supply_chain_investment == m.SUPPLY_CHAIN_MAX_UNITS
    assert farm.variation_enabled is False and farm.subsidy_rounds_left == 0 and farm.genetics_active == 0
