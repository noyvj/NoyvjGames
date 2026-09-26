"""G21: the one-time emergency region rescue."""


def _make_critical(r, funds=500.0):
    r.temperature = 17.0
    r.melt_started_round = 5
    r.funds = funds
    assert r.is_critical()


def test_rescue_unavailable_when_not_critical(game_env):
    r = game_env.region
    r.funds = 999
    assert not r.can_rescue()
    assert r.rescue() is False
    assert r.funds == 999
    assert r.rescue_used is False


def test_rescue_unavailable_without_funds(game_env):
    r = game_env.region
    _make_critical(r, funds=game_env.module.RESCUE_COST - 1)
    assert not r.can_rescue()
    assert r.rescue() is False


def test_rescue_spends_funds_and_starts_boost(game_env):
    m = game_env.module
    r = game_env.region
    _make_critical(r, funds=500.0)
    assert r.rescue() is True
    assert r.funds == 500.0 - m.RESCUE_COST
    assert r.rescue_used and r.rescue_rounds_left == m.RESCUE_DURATION_ROUNDS
    assert r.rescue_active()


def test_rescue_is_once_per_region(game_env):
    r = game_env.region
    _make_critical(r, funds=2000.0)
    assert r.rescue()
    r.rescue_rounds_left = 0  # boost lapsed
    assert r.can_rescue() is False
    assert r.rescue() is False


def test_rescue_boost_reduces_feedback_but_not_investment_dampening(game_env):
    m = game_env.module
    r = game_env.region
    _make_critical(r)
    plain = r.feedback_bonus()
    r.rescue()
    assert r.feedback_dampening_fraction() == 0.0  # achievements/readouts unaffected
    assert r.effective_dampening_fraction() == m.RESCUE_DAMPENING_BONUS
    assert r.feedback_bonus() < plain


def test_rescue_boost_is_capped_and_never_lowers_existing_dampening(game_env):
    m = game_env.module
    r = game_env.region
    _make_critical(r)
    r.rescue()
    r.capacity["preserve"] = 11  # investment now at the 0.85 cap
    assert r.effective_dampening_fraction() == m.RESCUE_MAX_DAMPENING


def test_rescue_expires_after_its_duration(game_env):
    m = game_env.module
    r = game_env.region
    _make_critical(r, funds=2000.0)
    r.rescue()
    for _ in range(m.RESCUE_DURATION_ROUNDS):
        assert r.rescue_active()
        r.advance_round()
    assert not r.rescue_active()
    assert r.effective_dampening_fraction() == r.feedback_dampening_fraction()


def test_rescue_slows_warming_versus_no_rescue(game_env):
    a = game_env.module.region_b
    b = game_env.module.region_c
    for r in (a, b):
        _make_critical(r, funds=2000.0)
    a.rescue()
    for _ in range(3):
        a.advance_round()
        b.advance_round()
    assert a.temperature < b.temperature


def test_rescue_button_visibility_and_click(game_env):
    m = game_env.module
    button = game_env.elements["rescue-button"]
    game_env.module.render()
    assert button.hidden is True
    _make_critical(game_env.region, funds=500.0)
    m.render()
    assert button.hidden is False and button.disabled is False
    button.dispatch("click", None)
    assert game_env.region.rescue_used
    assert game_env.region.funds == 500.0 - m.RESCUE_COST
    assert button.hidden is True
    assert "Rescue active" in game_env.elements["rescue-status"].innerText


def test_rescue_button_disabled_when_unaffordable(game_env):
    button = game_env.elements["rescue-button"]
    _make_critical(game_env.region, funds=10.0)
    game_env.module.render()
    assert button.hidden is False and button.disabled is True
    assert "costs" in game_env.elements["rescue-status"].innerText
    button.dispatch("click", None)  # a click on a disabled-state button changes nothing
    assert game_env.region.rescue_used is False


def test_secondary_region_rescue_button(game_env):
    m = game_env.module
    _make_critical(m.region_b, funds=500.0)
    m.render()
    button = game_env.elements["b-rescue-button"]
    assert button.hidden is False
    button.dispatch("click", None)
    assert m.region_b.rescue_used and not m.region.rescue_used
    assert game_env.elements["c-rescue-button"].hidden is True


def test_spent_status_shown_after_boost_lapses(game_env):
    m = game_env.module
    r = game_env.region
    _make_critical(r, funds=500.0)
    r.rescue()
    r.rescue_rounds_left = 0
    m.render()
    assert "spent" in game_env.elements["rescue-status"].innerText
    assert game_env.elements["rescue-button"].hidden is True


def test_save_round_trip_preserves_rescue(game_env):
    m = game_env.module
    _make_critical(game_env.region, funds=500.0)
    game_env.region.rescue()
    game_env.region.advance_round()
    data = m.get_state()
    assert data["region"]["rescue_used"] is True
    assert data["region"]["rescue_rounds_left"] == m.RESCUE_DURATION_ROUNDS - 1
    game_env.region.rescue_used = False
    game_env.region.rescue_rounds_left = 0
    m.load_state(data)
    assert game_env.region.rescue_used is True
    assert game_env.region.rescue_rounds_left == m.RESCUE_DURATION_ROUNDS - 1


def test_untouched_region_save_omits_rescue_fields(game_env):
    data = game_env.module.get_state()
    assert "rescue_used" not in data["region"]


def test_load_rejects_bad_rescue_values(game_env):
    m = game_env.module
    data = m.get_state()
    data["region"]["rescue_used"] = "yes"
    data["region"]["rescue_rounds_left"] = 999
    m.load_state(data)
    assert game_env.region.rescue_used is False
    assert game_env.region.rescue_rounds_left == 0
    data["region"]["rescue_rounds_left"] = -3
    m.load_state(data)
    assert game_env.region.rescue_rounds_left == 0
    data["region"]["rescue_rounds_left"] = True
    m.load_state(data)
    assert game_env.region.rescue_rounds_left == 0


def test_active_rescue_implies_used_on_load(game_env):
    m = game_env.module
    data = m.get_state()
    data["region"]["rescue_rounds_left"] = 3
    m.load_state(data)
    assert game_env.region.rescue_used is True
