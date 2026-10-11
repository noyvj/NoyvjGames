"""B-7: the game speaks through shared/announcer.js when the page loads it, else through its own live region,
and says what a sighted player sees change after each main action (never on a plain re-render)."""

import sys
import types

import pytest


@pytest.fixture
def said(game_env):
    """A recording stand-in for window.NoyvjAnnounce; removed again after the test."""
    messages = []
    sys.modules["js"].window = types.SimpleNamespace(NoyvjAnnounce=types.SimpleNamespace(say=messages.append))
    yield messages
    del sys.modules["js"].window


def _own_region(game_env):
    return game_env.elements["sr-announcer"].innerText


def test_announcements_go_through_the_shared_announcer_when_the_page_has_it(game_env, said):
    game_env.module.announce("Round 2 begins")
    assert said == ["Round 2 begins"]
    assert _own_region(game_env) in ("", None)


def test_without_the_shared_announcer_the_games_own_region_still_speaks(game_env):
    game_env.module.announce("Round 2 begins")
    assert _own_region(game_env) == "Round 2 begins"


def test_a_failing_shared_announcer_falls_back_and_never_breaks_the_game(game_env):
    def boom(_text):
        raise RuntimeError("announcer broke")

    sys.modules["js"].window = types.SimpleNamespace(NoyvjAnnounce=types.SimpleNamespace(say=boom))
    try:
        game_env.module.announce("Round 2 begins")
    finally:
        del sys.modules["js"].window
    assert _own_region(game_env) == "Round 2 begins"


def test_emoji_are_not_read_aloud(game_env, said):
    game_env.module.announce("\U0001F3DB️ Held the line! The wave passed")
    assert said == ["Held the line! The wave passed"]


def test_rendering_alone_announces_nothing(game_env, said):
    game_env.module.render()
    game_env.module.render()
    assert said == []


def test_investing_announces_the_new_capacity_funds_and_strain(game_env, said):
    funds_before = game_env.region.funds
    game_env.invest("housing")
    assert len(said) == 2  # the invest result, then the First Investment achievement
    text = said[0]
    assert said[1] == "Achievement unlocked: First Investment"
    assert "Invested in Housing" in text
    assert f"Total capacity {game_env.region.total_capacity():.0f}" in text
    assert f"Funds {funds_before - 20:.0f}" in text
    assert "Strain" in text


def test_a_refused_investment_says_why(game_env, said):
    game_env.region.funds = 5.0
    game_env.invest("services")
    assert said == ["Cannot invest in Integration Services: it costs 20 and you have 5"]
    assert game_env.region.funds == 5.0


def test_funding_a_policy_announces_its_level_and_a_refusal_says_why(game_env, said):
    game_env.elements["policy-credentialing-button"].dispatch("click", None)
    assert len(said) == 1
    assert "Funded Streamlined Credentialing, level 1 of 3" in said[0]
    said.clear()
    game_env.region.funds = 0.0
    game_env.elements["policy-credentialing-button"].dispatch("click", None)
    assert said and said[0].startswith("Cannot fund Streamlined Credentialing: it costs")
    said.clear()
    game_env.region.funds = 500.0
    game_env.region.policy_level["credentialing"] = game_env.module.POLICY_MAX_LEVEL
    game_env.elements["policy-credentialing-button"].dispatch("click", None)
    assert said == ["Streamlined Credentialing is already at its top level"]


def test_advancing_a_round_announces_the_recap_and_the_new_round(game_env, said):
    game_env.invest("housing")
    said.clear()
    game_env.advance_round()
    assert len(said) == 1
    text = said[0]
    assert text.startswith("Round 1: ")
    assert "arrived" in text and "integrated" in text
    assert "Round 2 begins:" in text
    assert f"Funds {game_env.region.funds:.0f}" in text
    assert "Strain" in text and "Wellbeing score" in text
    # the recap line is the one the Round recap panel already shows
    assert game_env.module.latest_recap().rstrip(".") in text


def test_a_second_wave_is_announced_only_when_its_status_changes(game_env, said):
    module = game_env.module
    marks = module._round_marks()
    game_env.region.second_wave_status = "warned"
    game_env.region.ledger.append(
        {"round": 1, "arrivals": 10, "integrated_new": 0, "shortfall": 0, "strain": 0.0, "income": 5, "spent": 0}
    )
    changed = module.round_announcement_text(marks)
    assert "second, larger wave" in changed
    unchanged = module.round_announcement_text(module._round_marks())
    assert "second, larger wave" not in unchanged


def test_the_net_positive_turning_point_is_announced_the_round_it_happens(game_env, said):
    module = game_env.module
    game_env.advance_round()
    marks = module._round_marks()
    assert marks[1] is None
    game_env.region.net_positive_round = 1
    assert "Turning point, round 1" in module.round_announcement_text(marks)
    assert "Turning point" not in module.round_announcement_text(module._round_marks())


def test_a_calendar_result_is_part_of_the_round_announcement(game_env, said):
    region = game_env.region
    region.calendar_enabled = True
    game_env.advance_round()
    region.calendar_log.append({"round": region.round_number - 1, "kind": "surge", "braced": False, "held": True})
    text = game_env.module.round_announcement_text()
    assert "capacity still covers everyone" in text
    game_env.module.announce(text)
    assert "capacity still covers everyone" in said[-1]
    assert "\U0001F30A" not in said[-1]


def test_play_five_rounds_announces_the_note_then_the_last_round(game_env, said):
    game_env.invest("housing")
    said.clear()
    game_env.elements["play-rounds-button"].dispatch("click", None)
    assert said[0].startswith("Played ")
    assert any("begins:" in message for message in said[1:])
    # the note is spoken by the announcer, not by a second live region
    assert game_env.elements["sr-announcer"].innerText in ("", None)


def test_reset_round_announces_the_refund_or_that_there_is_nothing_to_reset(game_env, said):
    game_env.elements["reset-round-button"].dispatch("click", None)
    assert said == ["Nothing to reset: you have not made a decision this round"]
    said.clear()
    game_env.invest("housing")
    said.clear()
    game_env.elements["reset-round-button"].dispatch("click", None)
    assert said == ["This round's decisions were refunded. Funds and capacity are back to the start of the round."]


def test_moving_capacity_announces_the_move_and_refusals(game_env, said):
    game_env.invest("housing")
    said.clear()
    game_env.elements["realloc-from"].value = "housing"
    game_env.elements["realloc-to"].value = "services"
    game_env.elements["realloc-button"].dispatch("click", None)
    assert said and said[0].startswith("Moved 10 capacity from Housing to Integration Services")
    said.clear()
    game_env.elements["realloc-to"].value = "housing"
    game_env.elements["realloc-button"].dispatch("click", None)
    assert said == ["Choose two different capacity types to move capacity between"]


def test_bracing_with_nothing_to_brace_says_so(game_env, said):
    game_env.elements["calendar-brace-button"].dispatch("click", None)
    assert said == ["Nothing to brace for right now"]


def test_neighbouring_district_actions_announce(game_env, said):
    game_env.region.round_number = game_env.module.NEIGHBOR_MIN_ROUND
    game_env.elements["neighbor-open-button"].dispatch("click", None)
    assert said and said[0].startswith("Neighbouring district opened")
    said.clear()
    game_env.region.funds = 0.0
    game_env.elements["neighbor-support-button"].dispatch("click", None)
    assert said and said[0].startswith("Cannot send support")


def test_an_achievement_unlock_is_announced_once(game_env, said):
    game_env.invest("housing")
    first = [m for m in said if m.startswith("Achievement unlocked")]
    assert len(first) <= 1
    assert game_env.module._achievements_seen_ids is not None
    said.clear()
    game_env.module._achievements_seen_ids = set()
    game_env.module._check_new_achievements_for_toast()
    unlocked = [m for m in said if "unlocked" in m]
    assert len(unlocked) == 1


def test_the_games_own_notes_are_not_second_live_regions():
    """The round-tools and calendar notes used to be role=status live regions of their own; the announcer now
    owns what they say, so they would be read twice."""
    from pathlib import Path

    html = (Path(__file__).resolve().parent.parent / "index.html").read_text(encoding="utf-8")
    for note in ("round-tools-note", "calendar-note"):
        line = next(row for row in html.splitlines() if f'id="{note}"' in row)
        assert "aria-live" not in line and "role=" not in line
    assert '<script src="../../shared/announcer.js"></script>' in html
    assert html.index("shared/announcer.js") < html.index("shared/last-played.js")
