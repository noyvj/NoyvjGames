"""Edge-case tests for story.py."""

import story


def test_unlocked_beats_empty_contact():
    """unlocked_beats returns an empty list when contact is empty."""
    assert story.unlocked_beats({}) == []


def test_unlocked_beats_partial_contact():
    """unlocked_beats returns only beats for planets present and true in contact."""
    contact = {"pulse": True}
    beats = story.unlocked_beats(contact)
    assert len(beats) == 1
    assert beats[0]["id"] == "planet1"


def test_unlocked_beats_full_contact():
    """unlocked_beats returns all beats in order when all planets are contacted."""
    contact = {"pulse": True, "compound": True, "bridge": True}
    beats = story.unlocked_beats(contact)
    assert len(beats) == 4
    assert [b["id"] for b in beats] == ["planet1", "planet2", "planet3", "closing"]


def test_unlocked_beats_missing_keys_ignored():
    """unlocked_beats ignores keys not in BEATS and treats missing keys as false."""
    contact = {"pulse": True, "unknown_planet": True}
    beats = story.unlocked_beats(contact)
    assert len(beats) == 1
    assert beats[0]["id"] == "planet1"


def test_unlocked_beats_false_values_treated_as_missing():
    """unlocked_beats treats False values in contact as missing."""
    contact = {"pulse": False, "compound": True}
    beats = story.unlocked_beats(contact)
    assert len(beats) == 1
    assert beats[0]["id"] == "planet2"


def test_view_empty_contact():
    """view returns the brief and an empty beat list when no planets are contacted."""
    v = story.view({})
    assert "brief" in v
    assert v["beats"] == []
    assert v["brief"]["id"] == "brief"


def test_view_full_contact():
    """view returns beats newest first when all planets are contacted."""
    contact = {"pulse": True, "compound": True, "bridge": True}
    v = story.view(contact)
    assert len(v["beats"]) == 4
    assert [b["id"] for b in v["beats"]] == ["closing", "planet3", "planet2", "planet1"]


def test_all_text_structure_and_length():
    """all_text returns a list of strings containing brief lines, beat titles, and beat lines."""
    text_list = story.all_text()
    assert isinstance(text_list, list)
    assert len(text_list) == 24
    assert all(isinstance(t, str) for t in text_list)
