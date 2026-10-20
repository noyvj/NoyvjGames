"""Edge-case tests for achievements.py."""

from state import Keep
import achievements
import sim


def test_refresh_on_fresh_keeper_returns_empty_and_changes_nothing():
    """A brand new keeper should earn nothing and leave meta untouched by refresh."""
    k = Keep(1)
    sim.to_evening(k)
    before = list(k.meta["achievements_earned"])
    new = achievements.refresh(k)
    assert new == []
    assert k.meta["achievements_earned"] == before


def test_refresh_with_maxed_counters_earns_all_keeping_achievements():
    """When all keeping counters are maxed out, refresh should return exactly the 11 keeping achievement ids."""
    k = Keep(42)
    sim.to_evening(k)
    k.meta.setdefault("counters", {})
    k.meta["counters"]["quiet_nights"] = 1
    k.meta["counters"]["fog_clears"] = 1
    k.meta["counters"]["storm_wardens"] = 1
    k.meta["counters"]["tidy_days"] = 1
    k.meta["counters"]["frugal_seasons"] = 1
    k.meta["nights_kept"] = 1
    k.meta["years"] = 1
    k.meta["counters"]["best_wound_streak"] = 7
    k.meta["counters"]["empty_nights"] = 1
    k.upgrades = ["bell"]
    k.mode = "endless"

    new = achievements.refresh(k)
    keeping_ids = {a[0] for a in achievements.ACHIEVEMENTS if not a[3]}
    assert set(new) == keeping_ids


def test_earned_ids_returns_empty_list_for_fresh_keeper():
    """A fresh keeper should have no earned achievement ids."""
    k = Keep(1)
    sim.to_evening(k)
    assert achievements.earned_ids(k) == []


def test_view_shows_hidden_mystery_achievements_as_mystery_when_unearned():
    """Unearned mystery achievements should display generic labels until solved."""
    k = Keep(1)
    sim.to_evening(k)
    view_list = achievements.view(k)
    hidden_in_view = [a for a in view_list if a["hidden"]]
    assert len(hidden_in_view) == 6
    assert all(a["label"] == "A mystery" and a["description"] == "Solve one of the odd happenings. Which one is for you to find out." for a in hidden_in_view)


def test_view_shows_correct_labels_when_mystery_achievement_is_earned():
    """Once a mystery achievement is earned, its label and description should be revealed."""
    k = Keep(1)
    sim.to_evening(k)
    k.meta["achievements_earned"].append("two_cups")
    view_list = achievements.view(k)
    two_cups_entry = next(a for a in view_list if a["id"] == "two_cups")
    assert two_cups_entry["label"] == "Two Cups"
    assert not two_cups_entry["hidden"]


def test_manifest_structure_matches_achievements_constant():
    """The manifest function should return exactly the id, label, and description for each achievement."""
    manifest = achievements.manifest()
    assert "achievements" in manifest
    assert len(manifest["achievements"]) == len(achievements.ACHIEVEMENTS)
    for i, (aid, label, desc, _, _) in enumerate(achievements.ACHIEVEMENTS):
        entry = manifest["achievements"][i]
        assert entry["id"] == aid
        assert entry["label"] == label
        assert entry["description"] == desc
