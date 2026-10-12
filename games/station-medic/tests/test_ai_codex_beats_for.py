"""Tests for the beats_for() function in codex.py."""

import codex
import cast
import progress


def test_beats_for_returns_empty_list_for_shift_with_no_beats():
    """Test that beats_for returns an empty list for a shift with no crew beats."""
    # Find a shift with no beats
    for sid in progress.ORDER:
        if not codex.BEATS_BY_SHIFT.get(sid, []):
            beats = codex.beats_for(sid)
            assert beats == []
            return
    assert False, "Could not find a shift with no beats"


def test_beats_for_returns_crew_beats_for_normal_shift():
    """Test that beats_for returns crew beats for a normal shift."""
    # Find a shift with crew beats
    for sid in progress.ORDER:
        beats = codex.BEATS_BY_SHIFT.get(sid, [])
        if beats:
            result = codex.beats_for(sid)
            assert len(result) == len(beats)
            for i, (crew_id, beat_idx) in enumerate(beats):
                assert result[i]["who"] == cast.CREW_BY_ID[crew_id]["name"]
                assert result[i]["text"] == cast.BEATS[crew_id][beat_idx]
            return
    assert False, "Could not find a shift with crew beats"


def test_beats_for_includes_tally_beats_when_robot_is_on_duty():
    """Test that beats_for includes Tally's beat when the robot is on duty."""
    # Find a shift with Tally on duty
    for sid in progress.ORDER:
        if sid in codex.TALLY_BY_SHIFT:
            result = codex.beats_for(sid)
            tally_beat_idx = codex.TALLY_BY_SHIFT[sid]
            assert any(b["who"] == "Tally" for b in result)
            assert any(b["text"] == cast.TALLY_BEATS[tally_beat_idx] for b in result)
            return
    assert False, "Could not find a shift with Tally on duty"
