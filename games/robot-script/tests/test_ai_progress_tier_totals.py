
import progress
import rooms


def test_tier_totals_normal_returns_base_totals():
    """Normal difficulty should return exactly the base totals without modification."""
    best = {"wake-up": {"n": 1, "t": "F"}}
    hbest = {}
    result = progress.tier_totals(best, hbest, "normal")
    assert result["rooms"] == len(rooms.ORDER)
    assert result["chapters"] == len(rooms.CHAPTER_LIST)
    # Normal medals are based on best, so cleared should match gold+silver+bronze
    assert result["cleared"] == result["gold"] + result["silver"] + result["bronze"]


def test_tier_totals_hard_uses_hbest_for_medals():
    """Hard difficulty recalculates medal counts from hbest while keeping rooms/chapters from base."""
    best = {"wake-up": {"n": 1, "t": "F"}}
    # Give wake-up a gold on hard (assuming par >= 1)
    hbest = {"wake-up": 1}

    result = progress.tier_totals(best, hbest, "hard")
    assert result["rooms"] == len(rooms.ORDER)
    assert result["chapters"] == len(rooms.CHAPTER_LIST)
    # Since we only have one room cleared in best and hbest, cleared should be 1
    assert result["cleared"] == 1


def test_tier_totals_hard_with_mismatched_best_and_hbest():
    """Edge case: rooms cleared in best but not in hbest should show as 0 medals on hard."""
    # Pick two rooms that definitely exist from the canonical order
    rid1, rid2 = rooms.ORDER[:2]
    best = {rid1: {"n": 1, "t": "F"}, rid2: {"n": 1, "t": "F"}}
    hbest = {}  # Nothing cleared on hard

    result = progress.tier_totals(best, hbest, "hard")
    assert result["rooms"] == len(rooms.ORDER)
    assert result["chapters"] == len(rooms.CHAPTER_LIST)
    # Medals should be 0 because hbest is empty, but rooms/chapters remain from base totals
    assert result["cleared"] == 0
    assert result["gold"] == 0
    assert result["silver"] == 0
    assert result["bronze"] == 0
