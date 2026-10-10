"""B-7: the game speaks through shared/announcer.js when the page loads it, else through its own live region,
and says what a sighted player sees change after each main action (never on a plain re-render)."""

import sys
import types
from pathlib import Path

import pytest


@pytest.fixture
def said(game_env):
    """A recording stand-in for window.NoyvjAnnounce; removed again after the test."""
    messages = []
    sys.modules["js"].window = types.SimpleNamespace(NoyvjAnnounce=types.SimpleNamespace(say=messages.append))
    yield messages
    del sys.modules["js"].window


def _without_achievements(messages):
    return [m for m in messages if "chievement" not in m]


def test_announcements_go_through_the_shared_announcer_when_the_page_has_it(game_env, said):
    game_env.module.announce("Round 2 begins")
    assert said == ["Round 2 begins"]
    assert game_env.elements["sr-announcer"].innerText in ("", None)


def test_without_the_shared_announcer_the_games_own_region_still_speaks(game_env):
    game_env.module.announce("Round 2 begins")
    assert game_env.elements["sr-announcer"].innerText == "Round 2 begins"


def test_a_failing_shared_announcer_falls_back_and_never_breaks_the_game(game_env):
    def boom(_text):
        raise RuntimeError("announcer broke")

    sys.modules["js"].window = types.SimpleNamespace(NoyvjAnnounce=types.SimpleNamespace(say=boom))
    try:
        game_env.module.announce("Round 2 begins")
    finally:
        del sys.modules["js"].window
    assert game_env.elements["sr-announcer"].innerText == "Round 2 begins"


def test_rendering_alone_announces_nothing(game_env, said):
    game_env.module.render()
    game_env.module.render()
    assert said == []


def test_building_announces_the_plant_the_count_and_the_funds(game_env, said):
    state = game_env.state
    cost = state.plant_cost("coal")
    funds_before = state.funds
    game_env.build("coal")
    text = _without_achievements(said)[0]
    assert text.startswith("Built a Coal plant, ")
    assert f"{state.plant_counts['coal']} Coal standing" in text
    assert f"Funds {funds_before - cost:.0f}" in text


def test_a_refused_build_says_why(game_env, said):
    game_env.state.funds = 1.0
    cost = game_env.state.plant_cost("nuclear")
    game_env.module._make_build_handler("nuclear")()
    assert said == [f"Cannot build Nuclear: it costs {cost:.0f} and you have 1"]
    assert game_env.state.plant_counts["nuclear"] == 0


def test_retiring_announces_the_refund(game_env, said):
    game_env.build("coal")
    game_env.build("coal")
    said.clear()
    before = game_env.state.funds
    game_env.retire("coal")
    gained = game_env.state.funds - before
    text = _without_achievements(said)[0]
    assert text.startswith("Retired a Coal plant. ")
    assert f"Refund {gained:.0f}" in text


def test_retiring_with_none_standing_says_so(game_env, said):
    game_env.module._make_retire_handler("battery")()
    assert said == ["Cannot retire Battery Storage: none are standing"]


def test_maintaining_announces_the_new_wear_and_a_refusal_says_why(game_env, said):
    game_env.build("coal")
    said.clear()
    game_env.maintain("coal")
    text = _without_achievements(said)[0]
    assert text.startswith("Maintained the Coal fleet. Wear now ")
    assert "%" in text
    said.clear()
    game_env.state.funds = 0.0
    game_env.module._make_maintain_handler("coal")()
    assert said and said[0].startswith("Cannot maintain Coal: it costs")
    said.clear()
    game_env.module._make_maintain_handler("battery")()
    assert said == ["Cannot maintain Battery Storage: none are standing"]


def test_advancing_a_round_announces_the_recap_the_shares_and_the_funds(game_env, said):
    game_env.build("solar")
    said.clear()
    game_env.advance_round()
    text = _without_achievements(said)[0]
    state = game_env.state
    assert text.startswith("Round 1 recap: net ")
    assert f"Now round {state.round_number}" in text
    assert f"Demand is now {state.demand:g} against capacity {state.total_capacity():g}" in text
    assert "Renewables are " in text and "fossil share " in text
    assert f"Funds {state.funds:.0f}" in text
    # the recap line is the one the Round recap panel already shows
    assert game_env.module.round_recap_text()[0] in text


def test_a_disruption_and_a_breakdown_are_named_in_the_round_announcement(game_env):
    module, state = game_env.module, game_env.state
    game_env.advance_round()
    state.last_event = {"type": "brownout", "revenue_loss": 12.0, "severity": 0.4, "cause_plant": "coal"}
    state.last_aging_event = {"plant": "gas", "repair_cost": 7.0}
    text = module.round_announcement_text()
    assert "Brownout! Coal generation strained the grid" in text
    assert "Aging breakdown! A Gas plant failed from wear (repair cost 7)" in text


def test_offers_and_the_fifty_percent_milestone_are_announced_with_the_round(game_env):
    module, state = game_env.module, game_env.state
    game_env.advance_round()
    state.policy_lever_available = True
    state.grant_offer = {"id": "clean_grant", "round": state.round_number}
    text = module.round_announcement_text(milestone_new=True)
    assert "A policy lever is on offer" in text
    assert "Offer: " in text
    assert "More than half your grid's capacity is now renewable" in text
    assert "More than half" not in module.round_announcement_text()


def test_a_round_announcement_is_empty_before_the_first_round(game_env):
    assert game_env.module.round_announcement_text() == ""


def test_auto_advance_announces_its_summary_and_the_last_round(game_env, said):
    game_env.elements["auto-advance-button"].dispatch("click", None)
    first = _without_achievements(said)
    assert first[0].startswith("Auto-advanced ")
    assert first[1].startswith("Round ")
    assert "recap" in first[1]
    assert game_env.elements["sr-announcer"].innerText in ("", None)


def test_auto_advance_refusal_is_announced(game_env, said):
    game_env.state.policy_lever_available = True
    game_env.elements["auto-advance-button"].dispatch("click", None)
    assert said == ["A policy lever is waiting for your decision first."]


def test_demand_response_announces_the_new_level_and_a_refusal_says_why(game_env, said):
    game_env.invest_demand_response()
    assert said and said[0].startswith("Invested in demand response, level 1. Demand now grows by ")
    said.clear()
    game_env.state.funds = 0.0
    game_env.module.on_invest_demand_response()
    assert said and said[0].startswith("Cannot invest in demand response: it costs")


def test_policy_levers_announce_their_choice(game_env, said):
    state = game_env.state
    state.policy_lever_available = True
    game_env.enact_carbon_pricing()
    assert said[-1].startswith("Carbon pricing enacted: fossil plants cost more to build for ")
    state.active_policy = None
    state.policy_lever_available = True
    said.clear()
    game_env.enact_renewable_subsidy()
    assert said[-1].startswith("Renewable subsidy enacted")
    state.policy_lever_available = True
    said.clear()
    game_env.decline_policy()
    assert said == ["Policy lever declined"]
    said.clear()
    game_env.decline_policy()
    assert said == ["No policy lever is on offer right now"]


def test_grants_and_undo_announce(game_env, said):
    state = game_env.state
    state.grant_offer = {"id": "clean_grant", "round": 1}
    game_env.elements["grant-accept-button"].dispatch("click", None)
    assert said == [state.last_grant_message]
    said.clear()
    game_env.build("coal")
    said.clear()
    game_env.elements["undo-build-button"].dispatch("click", None)
    assert said and said[0].startswith("Took back the Coal build. Refunded ")


def test_an_achievement_unlock_is_announced_without_the_trophy(game_env, said):
    game_env.build("coal")
    unlocked = [m for m in said if "chievement" in m]
    for message in unlocked:
        assert "\U0001F3C6" not in message
        assert message.startswith("Achievement unlocked: ") or "achievements unlocked: " in message


def test_the_games_own_status_lines_are_not_second_live_regions():
    """Auto-advance and grant messages used to be role=status live regions of their own; the announcer now owns
    what they say, so they would be read twice."""
    html = (Path(__file__).resolve().parent.parent / "index.html").read_text(encoding="utf-8")
    for note in ("auto-advance-status", "grant-message-display"):
        line = next(l for l in html.splitlines() if f'id="{note}"' in l)
        assert "role=" not in line and "aria-live" not in line
    assert '<script src="../../shared/announcer.js"></script>' in html
    assert html.index("shared/announcer.js") < html.index("shared/last-played.js")


def test_each_plant_row_is_a_labelled_group_so_its_buttons_have_context():
    html = (Path(__file__).resolve().parent.parent / "index.html").read_text(encoding="utf-8")
    for plant in ("coal", "gas", "nuclear", "solar", "wind", "hydro", "battery"):
        assert f'id="{plant}-row" data-plant="{plant}" role="group" aria-labelledby="{plant}-name"' in html
