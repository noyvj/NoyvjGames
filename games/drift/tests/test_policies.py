"""I3: the policy toolkit (named institutional levers beside the capacity split)."""

import pytest


def _click(env, policy):
    env.elements[f"policy-{policy.replace('_', '-')}-button"].dispatch("click", None)


def test_starts_at_level_zero_with_no_effect(game_env):
    m = game_env.module
    r = m.region
    assert r.policy_level == {"credentialing": 0, "language_access": 0, "sponsorship": 0}
    for policy in m.POLICIES:
        assert r.policy_effect(policy) == 0


def test_investing_spends_funds_and_raises_the_level(game_env):
    m = game_env.module
    m.region.funds = 500
    _click(game_env, "credentialing")
    assert m.region.policy_level["credentialing"] == 1
    assert m.region.funds == 500 - m.POLICY_BASE_COST


def test_cost_grows_and_levels_cap(game_env):
    m = game_env.module
    r = m.region
    r.funds = 100_000
    costs = []
    for _ in range(m.POLICY_MAX_LEVEL):
        costs.append(r.policy_cost("sponsorship"))
        assert r.invest_policy("sponsorship")
    assert costs == [m.POLICY_BASE_COST * n for n in (1, 2, 3)]
    assert r.invest_policy("sponsorship") is False


def test_needs_funds_and_known_policy(game_env):
    m = game_env.module
    m.region.funds = m.POLICY_BASE_COST - 1
    assert m.region.invest_policy("credentialing") is False
    m.region.funds = 10_000
    for bad in ("bogus", "", None):
        assert m.region.invest_policy(bad) is False


def test_credentialing_raises_integration_contribution(game_env):
    m = game_env.module
    r = m.region
    r.integrated_population = 100.0
    base = r.integration_contribution()
    r.policy_level["credentialing"] = 2
    assert r.integration_contribution() == pytest.approx(base * 1.30)


def test_language_access_raises_integration_throughput(game_env):
    m = game_env.module
    r = m.region
    r.capacity["services"] = 20.0
    r.total_arrivals = 1000.0
    base = r.integration_this_round()
    r.policy_level["language_access"] = 3
    assert r.integration_this_round() == pytest.approx(base * 1.45)


def test_sponsorship_lowers_strain(game_env):
    m = game_env.module
    r = m.region
    r.total_arrivals = 100.0
    base = r.strain_fraction()
    r.policy_level["sponsorship"] = 2
    assert r.strain_fraction() < base
    assert r.strain_fraction() == pytest.approx((100.0 - 12.0) / 100.0)


def test_sponsorship_cannot_push_strain_below_zero(game_env):
    m = game_env.module
    r = m.region
    r.total_arrivals = 5.0
    r.policy_level["sponsorship"] = 3
    assert r.strain_fraction() == 0.0


def test_capacity_investment_is_unaffected(game_env):
    m = game_env.module
    r = m.region
    r.funds = 1000
    r.policy_level["sponsorship"] = 3
    before = r.capacity["housing"]
    r.invest("housing")
    assert r.capacity["housing"] - before == m.CAPACITY_PER_INVESTMENT["housing"]


def test_display_shows_level_cost_and_maxed(game_env):
    m = game_env.module
    m.region.funds = 10_000
    _click(game_env, "language_access")
    assert "(1/3)" in game_env.elements["policy-language-access-name"].innerText
    assert "Fund (120)" in game_env.elements["policy-language-access-button"].innerText
    m.region.policy_level["language_access"] = 3
    m.render()
    assert game_env.elements["policy-language-access-button"].innerText == "Maxed"
    assert game_env.elements["policy-language-access-button"].disabled is True


def test_unaffordable_button_disabled(game_env):
    m = game_env.module
    m.region.funds = 1
    m.render()
    assert game_env.elements["policy-credentialing-button"].disabled is True


def test_save_round_trip_and_default_omits_key(game_env):
    m = game_env.module
    assert "policy_level" not in m.get_state()
    m.region.policy_level.update({"credentialing": 2, "sponsorship": 1})
    data = m.get_state()
    assert data["policy_level"] == {"credentialing": 2, "language_access": 0, "sponsorship": 1}
    m.region.policy_level = {p: 0 for p in m.POLICIES}
    m.load_state(data)
    assert m.region.policy_level == {"credentialing": 2, "language_access": 0, "sponsorship": 1}


def test_load_rejects_bad_values(game_env):
    m = game_env.module
    zero = {p: 0 for p in m.POLICIES}
    data = m.get_state()
    data["policy_level"] = {"credentialing": 9, "language_access": -1, "sponsorship": "2", "fake": 1}
    m.load_state(data)
    assert m.region.policy_level == zero
    for bad in ("x", [1], None, 3):
        data["policy_level"] = bad
        m.load_state(data)
        assert m.region.policy_level == zero
