import renown


def test_gain_handles_zero_and_large_values():
    assert renown.gain(0, 0) == 0
    assert renown.gain(100, 5) == 105


def test_families_returns_base_at_zero_and_all_above_max():
    assert renown.families(0) == ["produce", "textiles", "ceramics"]
    assert set(renown.families(200)) == {"produce", "textiles", "ceramics", "spices", "sweets"}


def test_archetypes_respects_threshold_boundaries():
    assert renown.archetypes(0) == set()
    assert renown.archetypes(74) == {"child", "tourist"}
    assert renown.archetypes(75) == {"child", "tourist", "crowd"}


def test_newly_unlocked_exact_and_overlapping_ranges():
    # Exactly at the threshold should be included
    assert "spices" in renown.newly_unlocked(0, 50)
    # Overlapping range that skips some unlocks
    result = renown.newly_unlocked(10, 40)
    assert set(result) == {"tourist"}
    # Range below first unlock returns empty
    assert renown.newly_unlocked(0, 9) == []


def test_next_unlock_returns_none_above_max_and_correct_between():
    assert renown.next_unlock(200) is None
    assert renown.next_unlock(31) == {"name": "the Spices crate", "need": 50}
