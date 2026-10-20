"""Tests for state.story_to_dict()."""

from state import new_story, story_to_dict


def test_empty_story_returns_empty_dict():
    """A fresh story with all defaults should serialise to an empty dict."""
    story = new_story()
    assert story_to_dict(story) == {}


def test_populated_story_includes_only_non_default_fields():
    """Only fields that hold non-default values should appear in the output."""
    story = new_story()
    story["met"] = {"sailor_a": 1}
    story["inbox"] = [{"id": "letter_1", "night": 5}]
    story["read"] = ["letter_1"]
    story["buffs"] = {"lens_cloth": 3}
    story["unease"] = 2
    story["tonight"] = "trifle_x"

    result = story_to_dict(story)

    assert set(result.keys()) == {"met", "inbox", "read", "buffs", "unease", "tonight"}
    assert result["met"] == {"sailor_a": 1}
    assert result["inbox"] == [{"id": "letter_1", "night": 5}]
    assert result["read"] == ["letter_1"]
    assert result["buffs"] == {"lens_cloth": 3}
    assert result["unease"] == 2
    assert result["tonight"] == "trifle_x"


def test_zero_and_empty_values_are_omitted():
    """Fields set to zero or empty collections must not appear in the serialised dict."""
    story = new_story()
    story["unease"] = 0
    story["buffs"] = {"lens_cloth": 0}
    story["trifles"] = {}
    story["explained"] = []
    story["tonight"] = ""

    result = story_to_dict(story)

    assert "unease" not in result
    assert "buffs" not in result
    assert "trifles" not in result
    assert "explained" not in result
    assert "tonight" not in result
