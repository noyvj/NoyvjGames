"""Tests for the crew_total() function in codex.py."""

import codex
import cast


def test_crew_total_basic():
    """crew_total() returns the total number of crew beats plus Tally beats."""
    expected = len(cast.CREW_IDS) * len(cast.BEAT_AT) + len(cast.TALLY_BEATS)
    assert codex.crew_total() == expected


def test_crew_total_with_empty_crew():
    """crew_total() handles the edge case of no crew members."""
    original_crew = cast.CREW_IDS
    original_beats = cast.BEAT_AT
    original_tally = cast.TALLY_BEATS

    try:
        cast.CREW_IDS = ()
        cast.BEAT_AT = ()
        cast.TALLY_BEATS = ()
        assert codex.crew_total() == 0
    finally:
        cast.CREW_IDS = original_crew
        cast.BEAT_AT = original_beats
        cast.TALLY_BEATS = original_tally


def test_crew_total_with_one_crew_one_beat():
    """crew_total() correctly calculates with one crew member and one beat."""
    original_crew = cast.CREW_IDS
    original_beats = cast.BEAT_AT
    original_tally = cast.TALLY_BEATS

    try:
        cast.CREW_IDS = ("crew1",)
        cast.BEAT_AT = (0,)
        cast.TALLY_BEATS = ("tally1",)
        assert codex.crew_total() == 2
    finally:
        cast.CREW_IDS = original_crew
        cast.BEAT_AT = original_beats
        cast.TALLY_BEATS = original_tally
