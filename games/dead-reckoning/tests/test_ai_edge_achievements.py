import achievements
from state import new_meta, new_record, FLAGS


CHAPTERS = [["a1", "a2"], ["b1", "b2"]]


def meta_with(stars=None, flags=(), practice=0):
    m = new_meta()
    for cid, n in (stars or {}).items():
        m["charts"][cid] = dict(new_record(), stars=n)
    m["flags"] = [f for f in FLAGS if f in flags]
    m["practice_seeds_played"] = practice
    return m


def test_earned_with_zero_practice_seeds_does_not_grant_practice_makes():
    """Test that zero practice seeds does not trigger the practice achievement."""
    meta = meta_with(practice=0)
    assert "practice_makes" not in achievements.earned(meta, CHAPTERS)


def test_earned_with_minimum_threshold_practice_seeds_grants_practice_makes():
    """Test that exactly ten practice seeds triggers the practice achievement."""
    meta = meta_with(practice=10)
    assert "practice_makes" in achievements.earned(meta, CHAPTERS)


def test_earned_with_negative_practice_seeds_does_not_grant_practice_makes():
    """Test that negative practice seeds are safely ignored by the threshold check."""
    meta = meta_with(practice=-5)
    assert "practice_makes" not in achievements.earned(meta, CHAPTERS)


def test_view_with_empty_chapters_returns_all_achievements_but_only_flag_based_earned():
    """Test that an empty chapters list returns all 15 achievements, marking only flag-based ones."""
    meta = meta_with(flags=["landfall"])
    v = achievements.view(meta, [])
    assert len(v) == 15
    earned_ids = [a["id"] for a in v if a["earned"]]
    assert earned_ids == ["first_landfall"]


def test_view_with_no_flags_and_empty_chapters_returns_all_achievements_unearned():
    """Test that no flags and empty chapters results in all achievements being unearned."""
    meta = meta_with()
    v = achievements.view(meta, [])
    assert len(v) == 15
    assert not any(a["earned"] for a in v)


def test_earned_with_all_known_flags_grants_all_flag_mapped_achievements():
    """Test that providing all known flags grants every flag-mapped achievement."""
    meta = meta_with(flags=list(achievements.FLAG_OF.values()))
    earned_ids = achievements.earned(meta, CHAPTERS)
    expected = set(achievements.FLAG_OF.keys())
    assert set(earned_ids) >= expected
