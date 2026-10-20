"""Edge-case tests for achievements.py."""


import achievements


def test_sixteen_found_with_empty_and_max_input():
    """sixteen_found() should return 0 for an empty list and 16 for all valid codes."""
    assert achievements.sixteen_found([]) == 0
    # There are exactly 16 codes where bits (2k, 2k+1) match for k in 0..3.
    all_two_input = [i for i in range(256) if achievements.is_two_input(i)]
    assert len(all_two_input) == 16
    assert achievements.sixteen_found(all_two_input) == 16


def test_progress_with_zero_and_large_stats():
    """progress() should handle zero stats and large stats without error or incorrect clamping."""
    meta_zero = {"levels": {}, "found": [], "stats": {"chips": 0, "flips": 0}}
    have_zero = achievements.progress(meta_zero)
    for aid in [a[0] for a in achievements.ACHIEVEMENTS]:
        assert have_zero[aid] == 0

    meta_large = {"levels": {}, "found": [], "stats": {"chips": 9999, "flips": 9999}}
    have_large = achievements.progress(meta_large)
    # hundred_chips and switch_flipper should reflect the large stats
    assert have_large["hundred_chips"] == 9999
    assert have_large["switch_flipper"] == 9999


def test_view_with_empty_meta():
    """view() should return a list of achievement dicts with have=0 and earned=False when meta is empty."""
    meta = {"levels": {}, "found": [], "stats": {"chips": 0, "flips": 0}}
    result = achievements.view(meta)
    assert len(result) == len(achievements.ACHIEVEMENTS)
    for item in result:
        assert item["have"] == 0
        assert item["earned"] is False


def test_goals_with_zero_and_excessive_count():
    """goals() should return an empty list when count is 0, and at most all open achievements otherwise."""
    meta = {"levels": {}, "found": [], "stats": {"chips": 0, "flips": 0}}
    assert achievements.goals(meta, count=0) == []
    result = achievements.goals(meta, count=100)
    assert len(result) <= len(achievements.ACHIEVEMENTS)


def test_earned_with_no_achievements():
    """earned() should return an empty list when no achievements are earned."""
    meta = {"levels": {}, "found": [], "stats": {"chips": 0, "flips": 0}}
    assert achievements.earned(meta) == []
