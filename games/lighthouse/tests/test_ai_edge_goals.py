"""Edge-case tests for goals.py covering zero inputs, boundary values, and state transitions."""

import data
import goals
from state import Keep


def keep_at(night=1, seed=3):
    k = Keep(seed)
    k.night = night
    return k


def test_rep_goal_returns_first_threshold_when_reputation_is_zero():
    """When reputation is zero, the first title threshold should be returned with have=0."""
    k = keep_at(1)
    k.reputation = 0
    g = goals.goals(k)
    rep_g = [x for x in g if x["id"] == "rep"][0]
    assert rep_g["have"] == 0
    assert rep_g["need"] > 0


def test_rep_goal_disappears_when_reputation_exceeds_all_thresholds():
    """When reputation exceeds the highest threshold, no reputation goal should be generated."""
    k = keep_at(1)
    max_threshold = max(t for t, _ in data.REP_TITLES)
    k.reputation = max_threshold + 1
    g = goals.goals(k)
    assert not any(x["id"] == "rep" for x in g)


def test_upgrade_goal_have_is_clamped_to_cost_when_salvage_exceeds_it():
    """When salvage exceeds the nearest upgrade cost, have is clamped to need, marking it done."""
    k = keep_at(1)
    k.salvage = 9999
    if not hasattr(k, 'upgrades'):
        k.upgrades = []
    g = goals.goals(k)
    up_g = [x for x in g if x["id"] == "upgrade"][0]
    assert up_g["have"] == up_g["need"]
    assert up_g["done"] is True


def test_upgrade_goal_disappears_when_all_upgrades_purchased():
    """When every upgrade id is in keep.upgrades, the upgrade goal should be omitted."""
    k = keep_at(1)
    k.upgrades = [u["id"] for u in data.UPGRADES]
    g = goals.goals(k)
    assert not any(x["id"] == "upgrade" for x in g)


def test_explore_goal_counters_default_to_zero_when_missing():
    """When meta.counters is empty, counters should default to 0 without raising KeyError."""
    k = keep_at(1)
    k.mode = "endless"  # Skip year goal logic to focus on ladder defaults
    if not hasattr(k, 'meta'):
        k.meta = {}
    k.meta["counters"] = {}
    g = goals.goals(k)
    exp_g = [x for x in g if x["id"] != "rep" and x["id"] != "upgrade"][0]
    assert exp_g["have"] == 0


def test_explore_goal_mend_is_done_when_all_parts_at_100_in_endless_mode():
    """In endless mode with all parts at 100, the mend goal should show have==need and done=True."""
    k = keep_at(1)
    k.mode = "endless"
    k.structure = {p: 100 for p in data.PARTS}
    # Satisfy all ladder conditions so _explore_goal falls through to 'mend'
    if not hasattr(k, 'meta'):
        k.meta = {}
    k.meta["counters"] = {
        "quiet_nights": 1, "tidy_days": 1, "fog_clears": 1, "storm_wardens": 1,
        "best_wound_streak": 7, "frugal_seasons": 1, "empty_nights": 1
    }
    g = goals.goals(k)
    mend_g = [x for x in g if x["id"] == "mend"][0]
    assert mend_g["have"] == mend_g["need"]
    assert mend_g["done"] is True
