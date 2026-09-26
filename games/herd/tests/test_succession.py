"""F25: farm succession (generations, legacy points, permanent perks)."""


def _certify(env):
    env.farm.certified = True


def _click(env, id_):
    env.elements[id_].dispatch("click", None)


def test_panel_hidden_until_certified(game_env):
    m = game_env.module
    m.render()
    assert game_env.elements["succession-panel"].hidden is True
    _certify(game_env)
    m.render()
    assert game_env.elements["succession-panel"].hidden is False
    assert game_env.elements["succession-button"].disabled is False


def test_cannot_hand_over_uncertified(game_env):
    m = game_env.module
    assert m.hand_over_farm() is None
    assert m.generation == 1 and m.legacy_points == 0


def test_handover_restarts_farm_and_awards_a_point(game_env):
    m = game_env.module
    old = game_env.farm
    old.herd_size = 40
    old.round_number = 30
    _certify(game_env)
    assert m.hand_over_farm() == 1
    assert m.generation == 2 and m.legacy_points == 1
    assert m.farm is not old
    assert m.farm.round_number == 1 and m.farm.certified is False
    assert m.farm.herd_size != 40


def test_flock_bonus_point_is_the_poultry_tie_in(game_env):
    m = game_env.module
    _certify(game_env)
    game_env.farm.poultry_size = m.SUCCESSION_FLOCK_MIN_SIZE
    assert m.handover_points() == 2
    game_env.farm.poultry_size = m.SUCCESSION_FLOCK_MIN_SIZE - 1
    assert m.handover_points() == 1


def test_button_click_runs_handover(game_env):
    m = game_env.module
    _certify(game_env)
    m.render()
    _click(game_env, "succession-button")
    assert m.generation == 2


def test_perks_need_points_and_respect_max(game_env):
    m = game_env.module
    assert m.buy_legacy_perk("family_savings") is False
    m.legacy_points = 10
    for _ in range(3):
        assert m.buy_legacy_perk("family_savings") is True
    assert m.buy_legacy_perk("family_savings") is False
    assert m.legacy_perks["family_savings"] == 3
    assert m.legacy_points == 7
    assert m.buy_legacy_perk("nonsense") is False


def test_family_savings_applies_now_and_to_every_new_generation(game_env):
    m = game_env.module
    m.legacy_points = 2
    funds = game_env.farm.funds
    cf = game_env.farm.counterfactual_funds
    assert m.buy_legacy_perk("family_savings")
    assert game_env.farm.funds == funds + m.FAMILY_SAVINGS_FUNDS
    assert game_env.farm.counterfactual_funds == cf + m.FAMILY_SAVINGS_FUNDS
    _certify(game_env)
    m.hand_over_farm()
    assert m.farm.funds == m.STARTING_FUNDS + m.FAMILY_SAVINGS_FUNDS
    assert m.farm.counterfactual_funds == m.STARTING_FUNDS + m.FAMILY_SAVINGS_FUNDS


def test_mentor_methods_gives_a_free_feed_unit(game_env):
    m = game_env.module
    m.legacy_points = 2
    assert m.buy_legacy_perk("mentor_methods")
    assert game_env.farm.decoupling_investment["feed"] == 1
    _certify(game_env)
    m.hand_over_farm()
    assert m.farm.decoupling_investment["feed"] == 1
    assert m.farm.coupling_ratio() < m.BASE_COUPLING_RATIO


def test_heritage_flock_unlocks_poultry_without_certification(game_env):
    m = game_env.module
    assert m.farm.poultry_unlocked() is False
    m.legacy_points = 2
    assert m.buy_legacy_perk("heritage_flock")
    assert m.farm.poultry_unlocked() is True
    _certify(game_env)
    m.hand_over_farm()
    assert m.farm.certified is False and m.farm.poultry_unlocked() is True
    m.render()
    assert game_env.elements["poultry-panel"].hidden is False


def test_perk_buttons_reflect_affordability(game_env):
    m = game_env.module
    m.legacy_points = 1
    m.render()
    assert game_env.elements["perk-family-savings-button"].disabled is False
    assert game_env.elements["perk-heritage-flock-button"].disabled is True
    _click(game_env, "perk-family-savings-button")
    assert m.legacy_perks["family_savings"] == 1 and m.legacy_points == 0


def test_save_round_trip(game_env):
    m = game_env.module
    _certify(game_env)
    m.hand_over_farm()
    m.legacy_points = 5
    m.buy_legacy_perk("family_savings")
    data = m.get_state()
    assert data["generation"] == 2 and data["legacy_points"] == 4
    assert data["legacy_perks"] == {"family_savings": 1}
    m.generation, m.legacy_points, m.legacy_perks = 1, 0, {}
    m.load_state(data)
    assert (m.generation, m.legacy_points, m.legacy_perks) == (2, 4, {"family_savings": 1})


def test_ordinary_save_omits_succession_keys(game_env):
    data = game_env.module.get_state()
    for key in ("generation", "legacy_points", "legacy_perks"):
        assert key not in data


def test_load_rejects_bad_succession_values(game_env):
    m = game_env.module
    data = m.get_state()
    data["generation"] = "x"
    data["legacy_points"] = -4
    data["legacy_perks"] = {"family_savings": 99, "heritage_flock": True, "fake": 3, "mentor_methods": "2"}
    m.load_state(data)
    assert m.generation == 1 and m.legacy_points == 0
    assert m.legacy_perks == {"family_savings": 3}
    data["legacy_perks"] = ["family_savings"]
    m.load_state(data)
    assert m.legacy_perks == {}


def test_handover_does_not_touch_meta_state_on_reload_of_module_farm(game_env):
    m = game_env.module
    _certify(game_env)
    m.hand_over_farm()
    m.legacy_points = 3
    m.hand_over_farm() if m.farm.certified else None
    assert m.generation == 2 and m.legacy_points == 3  # new farm is uncertified: no second handover
