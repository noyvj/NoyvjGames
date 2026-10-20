"""Tests for story.board_extras()."""

import sim
import story
import unease
from state import Keep


def test_board_extras_returns_empty_when_eerie_details_are_off():
    """When the player has turned off eerie details, ghost entries are hidden."""
    k = Keep(2)
    target_night = unease.schedule(2)["ws1"]
    k.night = target_night
    sim.to_evening(k)
    assert len(story.board_extras(k, target_night)) > 0
    k._eerie = False
    assert story.board_extras(k, target_night) == []


def test_board_extras_returns_empty_when_quiet_mode_is_active():
    """Quiet mode suppresses all story layer features, including ghost entries."""
    k = Keep(2)
    target_night = unease.schedule(2)["ws1"]
    k.night = target_night
    sim.to_evening(k)
    k.quiet = True
    assert story.board_extras(k, target_night) == []


def test_board_extras_returns_ghost_ship_names_for_scheduled_nights():
    """On a night with scheduled mystery beats that have board entries, it returns their names."""
    k = Keep(2)
    target_night = unease.schedule(2)["ws1"]
    k.night = target_night
    sim.to_evening(k)
    result = story.board_extras(k, target_night)
    expected = [b["board"] for _m, b in unease.beats_on(k.seed, k.night) if b.get("board")]
    assert result == expected


def test_board_extras_returns_empty_when_no_ghost_entries_are_scheduled():
    """On a night with no scheduled ghost entries, it returns an empty list."""
    k = Keep(2)
    # Pick a night far from ws1 to ensure no ghost entries are scheduled.
    k.night = 30
    sim.to_evening(k)
    assert story.board_extras(k, 30) == []
