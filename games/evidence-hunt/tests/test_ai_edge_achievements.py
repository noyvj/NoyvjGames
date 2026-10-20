"""Edge-case tests for achievements.py."""

import achievements
import lexicon


def test_earned_returns_empty_for_missing_facts():
    """earned should return [] when facts dict is empty or lacks required keys."""
    assert achievements.earned({}) == []
    assert achievements.earned({"done": 0}) == []


def test_earned_handles_exact_threshold():
    """earned should trigger exactly when fact value meets need."""
    # first_case needs "done" >= 1
    assert achievements.earned({"done": 1}) == ["first_case"]
    assert achievements.earned({"done": 0}) == []


def test_view_reports_zero_have_for_empty_facts():
    """view should report have=0 and earned=False for all achievements when facts are empty."""
    result = achievements.view({})
    for item in result:
        assert item["have"] == 0
        assert item["need"] > 0
        assert item["earned"] is False


def test_goals_respects_count_parameter():
    """goals should return at most count items, even if more are available."""
    facts = {"done": 0}
    open_chapters = 10
    # first_case has chapter gate 0, so it's eligible. goals returns up to count.
    assert len(achievements.goals(facts, open_chapters, count=0)) == 0
    assert len(achievements.goals(facts, open_chapters, count=1)) == 1


def test_goals_filters_by_open_chapters():
    """goals should only return achievements whose chapter gate is less than open_chapters."""
    # Provide facts that satisfy all chapter 0 and 1 achievements, leaving only chapter 2+ unearned
    facts = {
        "done": achievements.TOTAL,
        "chapters_done": 3,
        "clean": achievements.TOTAL,
        "readings": 60,
        "spirits_full": len(lexicon.KIND_IDS),
        "two": 0,
        "kept": len(lexicon.KS_IDS),
        "sandbox": 3,
        "mem": 5,
        "pages": achievements.GUIDE_TOTAL,
    }
    # With open_chapters=2, chapter 2 is not < 2, so two_at_once is excluded.
    assert len(achievements.goals(facts, open_chapters=2)) == 0
    # With open_chapters=3, chapter 2 is < 3, so two_at_once is included.
    assert len(achievements.goals(facts, open_chapters=3)) == 1


def test_goals_returns_empty_when_all_earned():
    """goals should return [] when all eligible achievements are already earned."""
    facts = {
        "done": achievements.TOTAL,
        "chapters_done": 3,
        "clean": achievements.TOTAL,
        "readings": 60,
        "spirits_full": len(lexicon.KIND_IDS),
        "two": 4,
        "kept": len(lexicon.KS_IDS),
        "sandbox": 3,
        "mem": 5,
        "pages": achievements.GUIDE_TOTAL,
    }
    assert achievements.goals(facts, open_chapters=10) == []
