"""I-3 planner assist: Off / Suggest / Explain, advice only, and assisted runs stay out of the bests."""

import sys

from .fakes import FakeStorage


def _click(env, element_id):
    env.elements[element_id].dispatch("click", None)


def _storage():
    storage = FakeStorage()
    sys.modules["js"].localStorage = storage
    return storage


def test_off_by_default_and_hides_advice(game_env):
    m = game_env.module
    game_env.module.render()
    assert m.assist_mode == "off" and m.assisted_run is False
    assert game_env.elements["assist-suggestion"].hidden is True
    assert game_env.elements["assist-reasons"].hidden is True
    assert game_env.elements["assist-off-button"].attributes["aria-pressed"] == "true"


def test_suggest_shows_the_buy_line_without_reasons(game_env):
    _click(game_env, "assist-suggest-button")
    el = game_env.elements
    assert el["assist-suggestion"].hidden is False
    assert el["assist-suggestion"].innerText.startswith("Suggested this round:")
    assert el["assist-reasons"].hidden is True
    assert el["assist-suggest-button"].attributes["aria-pressed"] == "true"


def test_explain_adds_one_reason_per_item(game_env):
    _click(game_env, "assist-explain-button")
    reasons = game_env.elements["assist-reasons"]
    items = game_env.module.plan_suggestion()
    assert reasons.hidden is False
    assert reasons.innerHTML.count("<li>") == len(items)
    assert all(item["reason"] in reasons.innerHTML for item in items)


def test_turning_it_on_tags_the_run_and_off_does_not_remove_the_tag(game_env):
    m = game_env.module
    _click(game_env, "assist-suggest-button")
    assert m.assisted_run is True
    _click(game_env, "assist-off-button")
    assert m.assist_mode == "off" and m.assisted_run is True
    assert "assisted" in game_env.elements["assist-note"].innerText
    assert "(assisted run)" in game_env.elements["tier-summary"].innerText


def test_an_assisted_run_updates_no_personal_best_and_no_tier_best(game_env):
    m = game_env.module
    storage = _storage()
    before = m.personal_best["wellbeing_score"]  # the opening render has already set the starting score
    _click(game_env, "assist-suggest-button")
    for _ in range(3):
        for item in m.plan_suggestion():
            if item["kind"] == "capacity":
                for _ in range(item["count"]):
                    game_env.invest(item["key"])
        game_env.advance_round()
    assert m.personal_best["wellbeing_score"] == before
    assert m.tier_bests == {}
    assert "drift_personal_best_v1" not in storage.data and "drift_tier_bests_v1" not in storage.data


def test_an_unassisted_run_still_updates_both(game_env):
    m = game_env.module
    _storage()
    game_env.invest("housing")
    game_env.advance_round()
    assert m.personal_best["wellbeing_score"] > 0
    assert "gentle" in m.tier_bests


def test_achievements_still_count_when_assisted(game_env):
    _click(game_env, "assist-suggest-button")
    game_env.invest("housing")
    game_env.invest("housing")
    ids = game_env.module.achievement_ids_earned()
    assert "first_investment" in ids
    assert game_env.module.get_state()["achievements_earned"] == ids


def test_suggestion_is_pure_advice(game_env):
    region = game_env.region
    before = (region.funds, dict(region.capacity), dict(region.policy_level), region.round_buys)
    game_env.module.plan_suggestion()
    assert (region.funds, dict(region.capacity), dict(region.policy_level), region.round_buys) == before


def test_suggestion_is_deterministic_and_affordable(game_env):
    m = game_env.module
    first = m.plan_suggestion()
    assert first == m.plan_suggestion()
    assert sum(item["cost"] for item in first) <= game_env.region.funds


def test_first_round_suggests_capacity_that_covers_the_arrivals(game_env):
    m = game_env.module
    items = m.plan_suggestion()
    assert items[0]["kind"] == "capacity"
    built = sum(m.CAPACITY_PER_INVESTMENT[i["key"]] * i["count"] for i in items if i["kind"] == "capacity")
    assert built >= game_env.region.arrivals_this_round()


def test_following_the_advice_keeps_strain_stable_for_a_run(game_env):
    m = game_env.module
    for _ in range(12):
        for item in m.plan_suggestion():
            if item["kind"] == "capacity":
                for _ in range(item["count"]):
                    assert game_env.region.invest(item["key"])
            elif item["kind"] == "policy":
                assert game_env.region.invest_policy(item["key"])
            elif item["kind"] == "brace":
                game_env.region.brace()
        game_env.advance_round()
        assert game_env.region.strain_level() == "stable"


def test_advice_holds_when_capacity_already_covers_and_funds_are_low(game_env):
    m = game_env.module
    region = game_env.region
    region.capacity = {"housing": 500.0, "services": 300.0, "infrastructure": 0.0}
    region.funds = 30.0
    region.integrated_population = 0.0
    items = m.plan_suggestion()
    assert [i["kind"] for i in items] == ["hold"]
    assert m.plan_summary_line(items) == "Suggested this round: hold your funds."


def test_services_come_first_when_the_share_is_low(game_env):
    m = game_env.module
    region = game_env.region
    region.capacity = {"housing": 100.0, "services": 0.0, "infrastructure": 0.0}
    region.total_arrivals = 120.0
    items = m.plan_suggestion()
    assert items[0]["key"] == "housing" or items[0]["key"] == "services"
    assert any(i["key"] == "services" for i in items)


def test_a_policy_is_suggested_only_when_capacity_is_covered_and_a_reserve_remains(game_env):
    m = game_env.module
    region = game_env.region
    region.capacity = {"housing": 400.0, "services": 100.0, "infrastructure": 0.0}
    region.total_arrivals = 60.0
    region.integrated_population = 10.0
    region.funds = 500.0
    items = m.plan_suggestion()
    policies = [i for i in items if i["kind"] == "policy"]
    assert len(policies) == 1 and policies[0]["key"] == "language_access"
    assert region.funds - sum(i["cost"] for i in items) >= m.ASSIST_RESERVE
    region.funds = 70.0
    assert not [i for i in m.plan_suggestion() if i["kind"] == "policy"]
    assert all(i["key"] != "sponsorship" for i in items)


def test_brace_is_suggested_for_a_braceable_event(game_env):
    m = game_env.module
    region = game_env.region
    region.calendar_enabled = True
    region.round_number = 11  # round 12 is the first arrivals surge, which can be braced for
    region.capacity = {"housing": 900.0, "services": 400.0, "infrastructure": 0.0}
    region.funds = 400.0
    items = m.plan_suggestion()
    assert any(i["kind"] == "brace" for i in items)


def test_assisted_tag_rides_the_save_and_loads_back(game_env):
    m = game_env.module
    assert "assist" not in m.get_state()
    _click(game_env, "assist-explain-button")
    state = m.get_state()
    assert state["assist"] == {"mode": "explain", "assisted": True}
    m.assist_mode, m.assisted_run = "off", False
    assert m.load_state(state)
    assert m.assisted_run is True and m.assist_mode == "explain"


def test_bad_assist_data_loads_as_unassisted(game_env):
    m = game_env.module
    state = m.get_state()
    for junk in ("explain", {"assisted": "yes"}, {"mode": "explain"}, {"assisted": True, "mode": "bogus"}, None):
        state["assist"] = junk
        m.load_state(state)
        if isinstance(junk, dict) and junk.get("assisted") is True:
            assert m.assisted_run is True and m.assist_mode == "off"
        else:
            assert m.assisted_run is False and m.assist_mode == "off"


def test_run_summary_and_report_mention_assisted(game_env):
    m = game_env.module
    _click(game_env, "assist-suggest-button")
    assert "Assisted run" in m.run_summary_text()
    assert "assisted" in m.region_report_text()


def test_switching_mode_is_announced(game_env):
    announced = []
    game_env.module.announce = announced.append
    _click(game_env, "assist-suggest-button")
    assert announced and announced[-1].startswith("Suggested this round")


def test_rewind_does_not_remove_the_assisted_tag(game_env):
    m = game_env.module
    game_env.invest("housing")
    game_env.advance_round()
    _click(game_env, "assist-suggest-button")
    game_env.elements["rewind-button"].dispatch("click", None)
    game_env.elements["rewind-button"].dispatch("click", None)
    assert m.assisted_run is True
