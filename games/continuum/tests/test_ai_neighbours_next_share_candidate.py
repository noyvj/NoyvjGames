"""Tests for next_share_candidate() in neighbours.py."""


import neighbours


def test_returns_the_most_recent_unshared_discovery():
    record = neighbours.default()
    researched = ["fire_keeping", "toolmaking", "irrigation"]
    costs = {"fire_keeping": 10.0, "toolmaking": 20.0, "irrigation": 30.0}
    assert neighbours.next_share_candidate(record, "n1", researched, costs) == "irrigation"


def test_skips_shared_discoveries_and_returns_the_next_one():
    record = neighbours.default()
    record["slots"]["n2"]["shared"] = ["toolmaking"]
    researched = ["fire_keeping", "toolmaking", "irrigation"]
    costs = {"fire_keeping": 10.0, "toolmaking": 20.0, "irrigation": 30.0}
    assert neighbours.next_share_candidate(record, "n2", researched, costs) == "irrigation"


def test_returns_none_when_all_discoveries_are_shared_or_missing_costs():
    record = neighbours.default()
    record["slots"]["n3"]["shared"] = ["fire_keeping", "toolmaking", "irrigation"]
    researched = ["fire_keeping", "toolmaking", "irrigation"]
    costs = {"fire_keeping": 10.0, "toolmaking": 20.0}
    assert neighbours.next_share_candidate(record, "n3", researched, costs) is None
