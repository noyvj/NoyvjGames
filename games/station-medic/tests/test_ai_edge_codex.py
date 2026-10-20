"""Edge-case tests for codex.py."""

import codex
import progress


def test_beats_told_returns_empty_for_no_shifts_done():
    """Test that beats_told returns an empty list when no shifts are completed."""
    assert codex.beats_told({}) == []


def test_beats_told_includes_beats_for_real_shift():
    """Test that beats_told correctly includes beats for a shift with crew beats."""
    # Find a shift with beats using the same pattern as test_ai_codex_beats_for.py
    for sid in progress.ORDER:
        if codex.BEATS_BY_SHIFT.get(sid, []):
            result = codex.beats_told({sid: 1})
            expected = [(c, k) for c, k in codex.BEATS_BY_SHIFT[sid]]
            assert set(result) == set(expected)
            return
    assert False, "Could not find a shift with beats"


def test_tally_told_returns_empty_for_no_shifts_done():
    """Test that tally_told returns an empty list when no shifts are completed."""
    assert codex.tally_told({}) == []


def test_counts_returns_zero_found_with_empty_inputs():
    """Test that counts returns 0 found when all inputs are empty."""
    found, total = codex.counts({}, {}, {}, {})
    assert found == 0
    assert total > 0


def test_crew_total_returns_positive_integer():
    """Test that crew_total returns a positive integer representing the total crew beats."""
    total = codex.crew_total()
    assert isinstance(total, int)
    assert total > 0


def test_view_with_empty_inputs_produces_valid_structure():
    """Test that view returns a valid structure with 0 found when all inputs are empty."""
    result = codex.view({}, {}, {}, {})
    assert "notice" in result
    assert "sections" in result
    assert "found" in result
    assert "total" in result
    assert "crew_told" in result
    assert result["found"] == 0


def test_beats_for_returns_empty_for_nonexistent_shift():
    """Test that beats_for returns an empty list for a shift ID not in the game data."""
    assert codex.beats_for("99-9") == []
