"""Tests for the crew_told() function in codex.py."""

import codex
import progress


def test_crew_told_returns_zero_for_empty_best():
    """crew_told() returns 0 when no shifts are completed."""
    assert codex.crew_told({}) == 0


def test_crew_told_counts_crew_beats_and_tally_beats():
    """crew_told() counts both crew beats and Tally beats from completed shifts."""
    # Complete shifts that have crew beats and Tally beats
    best = {sid: 3 for sid in progress.ORDER[:10]}
    result = codex.crew_told(best)
    # Should count crew beats from first 10 shifts + Tally beats from robot shifts
    expected_crew = len(codex.beats_told(best))
    expected_tally = len(codex.tally_told(best))
    assert result == expected_crew + expected_tally


def test_crew_told_edge_case_all_shifts_completed():
    """crew_told() returns correct count when all shifts are completed."""
    # Complete all shifts
    best = {sid: 3 for sid in progress.ORDER}
    result = codex.crew_told(best)
    # Should count all crew beats + all Tally beats
    expected_crew = len(codex.beats_told(best))
    expected_tally = len(codex.tally_told(best))
    assert result == expected_crew + expected_tally
