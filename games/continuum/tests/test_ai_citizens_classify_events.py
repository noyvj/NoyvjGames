"""Tests for citizens.classify_events()."""

import citizens


def test_hunger_detected_from_deaths():
    report = {"deaths": 2}
    kinds, _ = citizens.classify_events(report, [], season=5)
    assert "hunger" in kinds


def test_research_detected_from_matching_motion():
    report = {}
    motions = [{"season": 5, "kind": "research", "text": "study X."}]
    kinds, details = citizens.classify_events(report, motions, season=5)
    assert "research" in kinds
    assert details["research"] == "X"


def test_calm_fallback_when_no_matching_events():
    report = {}
    motions = [{"season": 4, "kind": "build", "text": "build Y."}]
    kinds, _ = citizens.classify_events(report, motions, season=5)
    assert kinds == {"calm"}
