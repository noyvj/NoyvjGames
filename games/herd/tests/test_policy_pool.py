"""F-9 policy-advisor offer pool (planning/TODO.md "GF + F. Herd")."""

import json
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent.parent


def _offer(env, round_number=None):
    farm = env.farm
    farm.policy_offer_pending = True
    farm.policy_offer = farm.draw_policy_offer()
    return list(farm.policy_offer)


def test_first_offer_is_the_original_pair(game_env):
    m = game_env.module
    farm = game_env.farm
    for _ in range(m.POLICY_EVENT_INTERVAL - 1):
        farm.advance_round()
    assert farm.policy_offer_pending and farm.policy_offer == ["subsidy", "cash"]


def test_offers_never_repeat_until_the_pool_is_used(game_env):
    m = game_env.module
    farm = game_env.farm
    seen = []
    for _ in range(3):
        offer = _offer(game_env)
        assert len(set(offer)) == 2
        seen += offer
        farm.choose_policy(offer[0])
    assert sorted(seen) == sorted(m.POLICY_ORDER)  # three offers cover all six options exactly once
    fourth = _offer(game_env)
    assert fourth == ["subsidy", "cash"] or len(set(fourth)) == 2  # the cycle starts over


def test_draw_is_deterministic(game_env):
    farm = game_env.farm
    farm.policy_seen, farm.policy_history = [], []
    first = farm.draw_policy_offer()
    farm.policy_seen, farm.policy_history = [], []
    assert farm.draw_policy_offer() == first


def test_cannot_take_an_option_that_is_not_on_the_table(game_env):
    farm = game_env.farm
    farm.policy_offer_pending = True
    farm.policy_offer = ["carbon_credit", "feed_hedge"]
    assert farm.choose_policy("cash") is False
    assert farm.policy_offer_pending is True
    assert farm.choose_policy("nonsense") is False


def test_carbon_credit_pays_more_the_more_decoupled(game_env):
    farm = game_env.farm
    base = farm.carbon_credit_value()
    assert base == game_env.module.POLICY_CARBON_BASE
    farm.decoupling_investment["capture"] = 5
    assert farm.carbon_credit_value() > base
    farm.policy_offer_pending, farm.policy_offer = True, ["carbon_credit", "welfare_grant"]
    funds = farm.funds
    value = farm.carbon_credit_value()
    farm.choose_policy("carbon_credit")
    assert farm.funds == funds + value


def test_welfare_grant_pays_more_with_higher_welfare(game_env):
    farm = game_env.farm
    assert farm.welfare_grant_value() == game_env.module.POLICY_WELFARE_BASE
    farm.decoupling_investment["feed"] = 4  # +20 welfare
    assert farm.welfare_grant_value() > game_env.module.POLICY_WELFARE_BASE


def test_feed_hedge_halves_feed_for_six_rounds_only(game_env):
    m = game_env.module
    farm = game_env.farm
    farm.policy_offer_pending, farm.policy_offer = True, ["feed_hedge", "organic_trial"]
    farm.choose_policy("feed_hedge")
    assert farm.decoupling_cost("feed") == pytest.approx(m.DECOUPLING_MEASURES["feed"]["cost"] / 2)
    assert farm.decoupling_cost("caps") == m.DECOUPLING_MEASURES["caps"]["cost"]
    for _ in range(m.POLICY_HEDGE_ROUNDS):
        farm.advance_round()
    assert farm.decoupling_cost("feed") == m.DECOUPLING_MEASURES["feed"]["cost"]


def test_hedge_and_subsidy_stack(game_env):
    m = game_env.module
    farm = game_env.farm
    farm.subsidy_rounds_left = 2
    farm.hedge_rounds_left = 2
    assert farm.decoupling_cost("feed") == pytest.approx(
        m.DECOUPLING_MEASURES["feed"]["cost"] * (1 - m.POLICY_SUBSIDY_DISCOUNT) * (1 - m.POLICY_HEDGE_DISCOUNT)
    )


def test_organic_label_lifts_income_for_four_rounds_and_the_inspector_agrees(game_env):
    m = game_env.module
    farm = game_env.farm
    farm.herd_size = 10
    plain = farm.income_breakdown()["total"]
    farm.policy_offer_pending, farm.policy_offer = True, ["organic_trial", "welfare_grant"]
    farm.choose_policy("organic_trial")
    assert farm.income_breakdown()["total"] == pytest.approx(plain * (1 + m.POLICY_LABEL_BONUS))
    m.explain_kind = "income"
    assert "Organic label trial" in m.explain_html("income")
    funds = farm.funds
    farm.advance_round()
    assert farm.funds - funds == pytest.approx(plain * (1 + m.POLICY_LABEL_BONUS))
    for _ in range(m.POLICY_LABEL_ROUNDS):
        farm.advance_round()
    assert farm.label_multiplier() == 1.0


def test_buttons_show_the_offered_options_and_a_click_takes_one(game_env):
    m = game_env.module
    farm = game_env.farm
    farm.policy_offer_pending, farm.policy_offer = True, ["carbon_credit", "organic_trial"]
    m.render()
    assert "Carbon-credit contract" in game_env.elements["policy-subsidy-button"].innerText
    assert "Eco-label" in game_env.elements["policy-cash-button"].innerText
    assert "carbon-credit" in game_env.elements["policy-real-display"].innerText.lower()
    game_env.elements["policy-cash-button"].dispatch("click", None)
    assert farm.label_rounds_left == m.POLICY_LABEL_ROUNDS and not farm.policy_offer_pending
    assert farm.policy_history == [[1, "organic_trial", "carbon_credit"]]
    assert "took Organic label trial" in game_env.elements["policy-history-list"].innerHTML
    assert "Organic label trial" in m.policy_report_line()


def test_history_is_capped_and_report_card_lists_it(game_env):
    m = game_env.module
    farm = game_env.farm
    for i in range(m.POLICY_HISTORY_MAX + 5):
        farm.policy_offer_pending, farm.policy_offer = True, ["subsidy", "cash"]
        farm.choose_policy("cash")
    assert len(farm.policy_history) == m.POLICY_HISTORY_MAX
    assert "Advisor choices" in m.report_card_html()


def test_save_keys_only_when_set_and_round_trip(game_env):
    m = game_env.module
    farm = game_env.farm
    state = m.get_state()
    for key in ("policy_offer", "policy_seen", "policy_history", "hedge_rounds_left", "label_rounds_left"):
        assert key not in state
    farm.policy_offer_pending, farm.policy_offer, farm.policy_seen = True, ["feed_hedge", "welfare_grant"], ["subsidy", "cash", "feed_hedge", "welfare_grant"]
    farm.policy_history = [[8, "cash", "subsidy"]]
    farm.hedge_rounds_left, farm.label_rounds_left = 3, 2
    state = json.loads(json.dumps(m.get_state()))
    m.load_state({})
    assert m.farm.policy_offer == []
    m.load_state(state)
    f = m.farm
    assert f.policy_offer == ["feed_hedge", "welfare_grant"] and f.policy_history == [[8, "cash", "subsidy"]]
    assert (f.hedge_rounds_left, f.label_rounds_left) == (3, 2)
    assert f.policy_seen == ["subsidy", "cash", "feed_hedge", "welfare_grant"]


def test_bad_saved_policy_values_are_ignored(game_env):
    m = game_env.module
    m.load_state({
        "policy_offer_pending": True, "policy_offer": ["cash", "cash"], "policy_seen": ["cash", "cash", "bogus", 3],
        "policy_history": [[1, "cash", "cash"], [2, "bogus", "cash"], "x", [3, "cash", "subsidy"]],
        "hedge_rounds_left": 99, "label_rounds_left": "lots",
    })
    f = m.farm
    assert f.policy_offer == [] and f.current_policy_offer() == ["subsidy", "cash"]
    assert f.policy_seen == ["cash"]
    assert f.policy_history == [[3, "cash", "subsidy"]]
    assert f.hedge_rounds_left == m.POLICY_HEDGE_ROUNDS and f.label_rounds_left == 0


def test_an_older_save_with_a_pending_offer_still_works(game_env):
    m = game_env.module
    m.load_state({"policy_offer_pending": True})
    game_env.elements["policy-cash-button"].dispatch("click", None)
    assert m.farm.funds == m.STARTING_FUNDS + m.POLICY_CASH_BONUS


def test_every_option_has_a_real_world_tag_and_no_figures():
    import re
    text = (HERE / "game.py").read_text(encoding="utf-8")
    block = text[text.index("POLICY_OPTIONS = {"):text.index("POLICY_HEDGE_DISCOUNT")]
    for real in re.findall(r'"real": "([^"]+)"', block):
        assert real.startswith("Real-world idea:") and not re.search(r"\d", real)


def test_pages_have_the_history_and_real_world_elements():
    for page in ("index.html", "pc.html"):
        html = (HERE / page).read_text(encoding="utf-8")
        assert 'id="policy-history-list"' in html and 'id="policy-real-display"' in html
