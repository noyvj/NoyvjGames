"""G13: the optional starting policy stance for Region A."""


def _click(env, key):
    env.elements[f"policy-stance-{key}-button"].dispatch("click", None)


def test_no_stance_by_default_and_buttons_enabled(game_env):
    game_env.module.render()
    assert game_env.region.policy_stance is None
    for key in game_env.module.POLICY_STANCES:
        assert game_env.elements[f"policy-stance-{key}-button"].disabled is False
    assert "Optional" in game_env.elements["policy-stance-display"].innerText


def test_growth_stance_adds_funds_but_no_dampening(game_env):
    start = game_env.region.funds
    _click(game_env, "growth")
    assert game_env.region.policy_stance == "growth"
    assert game_env.region.funds == start + 100.0
    assert game_env.region.feedback_dampening_fraction() == 0.0


def test_mitigation_stance_adds_dampening_but_no_funds(game_env):
    start = game_env.region.funds
    _click(game_env, "mitigation")
    assert game_env.region.funds == start
    assert game_env.region.feedback_dampening_fraction() == 0.06


def test_balanced_stance_is_a_middle_path(game_env):
    start = game_env.region.funds
    _click(game_env, "balanced")
    assert game_env.region.funds == start + 40.0
    assert game_env.region.feedback_dampening_fraction() == 0.03


def test_stance_can_only_be_chosen_once(game_env):
    _click(game_env, "growth")
    funds = game_env.region.funds
    _click(game_env, "mitigation")
    assert game_env.region.policy_stance == "growth"
    assert game_env.region.funds == funds
    for key in game_env.module.POLICY_STANCES:
        assert game_env.elements[f"policy-stance-{key}-button"].disabled is True


def test_stance_locked_after_first_round(game_env):
    game_env.advance_round()
    assert game_env.region.can_choose_policy_stance() is False
    _click(game_env, "growth")
    assert game_env.region.policy_stance is None
    assert "No starting policy stance" in game_env.elements["policy-stance-display"].innerText


def test_stance_locked_after_first_investment(game_env):
    game_env.invest("output")
    _click(game_env, "growth")
    assert game_env.region.policy_stance is None


def test_unknown_stance_rejected(game_env):
    assert game_env.region.choose_policy_stance("nonsense") is False
    assert game_env.region.policy_stance is None


def test_stance_is_not_an_investment_for_achievements_or_praise(game_env):
    m = game_env.module
    _click(game_env, "mitigation")
    assert m.ACHIEVEMENT_CHECKS["first_intervention"]() is False
    r = game_env.region
    r.temperature = 9.5
    r.advance_round()
    assert r.just_preempted_melt is False  # no preserve/monitor invested


def test_stance_dampening_still_capped(game_env):
    m = game_env.module
    _click(game_env, "mitigation")
    game_env.region.capacity["preserve"] = 20
    assert game_env.region.feedback_dampening_fraction() == m.MAX_FEEDBACK_DAMPENING


def test_stance_slows_feedback_versus_none(game_env):
    m = game_env.module
    m.region_b.temperature = m.region_c.temperature = 14.0
    m.region_b.choose_policy_stance("mitigation")
    assert m.region_b.feedback_bonus() < m.region_c.feedback_bonus()


def test_message_names_the_stance_when_nothing_invested(game_env):
    _click(game_env, "mitigation")
    assert "policy stance" in game_env.region.intervention_feedback_message()


def test_save_round_trip_preserves_stance(game_env):
    m = game_env.module
    _click(game_env, "mitigation")
    data = m.get_state()
    assert data["region"]["policy_stance"] == "mitigation"
    game_env.region.policy_stance = None
    game_env.region.policy_dampening = 0.0
    m.load_state(data)
    assert game_env.region.policy_stance == "mitigation"
    assert game_env.region.policy_dampening == 0.06


def test_untouched_save_omits_stance(game_env):
    assert "policy_stance" not in game_env.module.get_state()["region"]


def test_load_rejects_bad_stance_values(game_env):
    m = game_env.module
    for bad in ("bogus", 7, ["growth"], {"a": 1}, None):
        data = m.get_state()
        data["region"]["policy_stance"] = bad
        m.load_state(data)
        assert game_env.region.policy_stance is None
        assert game_env.region.policy_dampening == 0.0
