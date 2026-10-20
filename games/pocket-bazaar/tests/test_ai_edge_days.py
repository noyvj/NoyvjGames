import pytest

import days


def test_spec_rejects_zero_and_negative_days():
    """Day numbers must start at 1."""
    for n in (0, -1, -100):
        with pytest.raises(ValueError, match="day numbers start at 1"):
            days.spec(n)


def test_spec_day_1_returns_campaign_defaults():
    """The first day uses the hand-tuned recipe from _TABLE."""
    s = days.spec(1)
    assert s["number"] == 1
    assert s["customers"] == 6
    assert s["max_tier"] == 2
    assert s["slack_pct"] == 450


def test_spec_day_10_is_last_campaign_day():
    """Day 10 marks the end of the hand-tuned campaign."""
    s = days.spec(10)
    assert s["number"] == 10
    assert s["customers"] == 12
    assert s["max_tier"] == 5


def test_spec_free_stall_clamps_customers_at_max():
    """Free Stall days gradually increase customers but never exceed MAX_CUSTOMERS."""
    s = days.spec(100)
    assert s["customers"] == days.MAX_CUSTOMERS
    assert s["slack_pct"] == 200


def test_spec_unlocked_archetypes_filters_correctly():
    """Passing unlocked_archetypes restricts the day's archetypes."""
    s = days.spec(4, unlocked_archetypes={"haggler"})
    assert s["archetypes"] == (("haggler", 1),)
    s_empty = days.spec(4, unlocked_archetypes=set())
    assert s_empty["archetypes"] == (("regular", 1),)


def test_spec_extras_adds_renown_archetypes():
    """extras parameter mixes in child, tourist, or crowd with their weights."""
    s = days.spec(1, extras=("child", "tourist"))
    assert ("child", 2) in s["archetypes"]
    assert ("tourist", 2) in s["archetypes"]
    assert ("crowd", 1) not in s["archetypes"]
