"""Tests for story.unlocked_beats()."""


import story


def test_empty_contact_returns_no_beats():
    """Edge case: no planets contacted yields an empty list."""
    assert story.unlocked_beats({}) == []


def test_single_planet_contact_returns_oldest_first():
    """Normal case: contacting only the first planet returns just its beat."""
    contact = {"pulse": True}
    result = story.unlocked_beats(contact)
    assert len(result) == 1
    assert result[0]["id"] == "planet1"


def test_multiple_planets_preserves_order():
    """Normal case: contacting multiple planets returns their beats in the order they appear in the data."""
    contact = {"pulse": True, "compound": True, "bridge": True}
    result = story.unlocked_beats(contact)
    assert [b["id"] for b in result] == ["planet1", "planet2", "planet3", "closing"]
