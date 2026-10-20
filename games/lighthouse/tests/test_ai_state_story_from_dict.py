"""Tests for state.story_from_dict()."""

import state
import lore
import mysteries


def test_normal_case_valid_structure_is_parsed_and_invalid_keys_are_dropped():
    """Valid keys are kept, invalid keys are filtered out by lore/mysteries checks."""
    real_sailor = list(lore.SAILORS.keys())[0] if lore.SAILORS else "test_sailor"
    real_letter = list(lore.LETTERS.keys())[0] if lore.LETTERS else "test_letter"
    real_gift = list(lore.GIFTS.keys())[0] if lore.GIFTS else "test_gift"
    real_trifle = list(mysteries.TRIFLES.keys())[0] if mysteries.TRIFLES else "test_trifle"

    raw = {
        "met": {real_sailor: 5, "invalid_key": 10},
        "inbox": [{"id": real_letter, "night": 3}],
        "read": [real_letter],
        "gifts": [real_gift],
        "choices": {real_letter: ["reply_key", 2]},
        "buffs": {"lens_cloth": 5},
        "beats": [["beat_id", 1]],
        "unease": 10,
        "trifles": {real_trifle: 2},
        "explained": [real_trifle],
        "tonight": real_trifle
    }
    result = state.story_from_dict(raw)
    assert result["met"][real_sailor] == 5
    assert len(result["met"]) == 1
    assert len(result["inbox"]) == 1
    assert result["read"] == [real_letter]
    assert result["gifts"] == [real_gift]
    assert result["buffs"]["lens_cloth"] == 5
    assert result["unease"] == 10
    assert result["trifles"][real_trifle] == 2
    assert real_trifle in result["explained"]
    assert result["tonight"] == real_trifle


def test_normal_case_none_values_and_duplicate_inbox():
    """None values fall back to defaults; inbox deduplicates by id."""
    real_letter = list(lore.LETTERS.keys())[0] if lore.LETTERS else "test_letter"
    raw = {
        "met": None,
        "inbox": [{"id": real_letter, "night": 3}, {"id": real_letter, "night": 5}],
        "read": None,
        "gifts": None,
        "choices": None,
        "buffs": None,
        "beats": None,
        "unease": -5,
        "trifles": None,
        "explained": None,
        "tonight": None
    }
    result = state.story_from_dict(raw)
    assert result["met"] == {}
    assert len(result["inbox"]) == 1
    assert result["inbox"][0]["night"] == 3
    assert result["read"] == []
    assert result["gifts"] == []
    assert result["choices"] == {}
    assert result["buffs"] == {}
    assert result["beats"] == []
    assert result["unease"] == 0
    assert result["trifles"] == {}
    assert result["explained"] == []
    assert result["tonight"] == ""


def test_edge_case_empty_input_returns_default_story():
    """Passing an empty dict should yield exactly new_story()."""
    result = state.story_from_dict({})
    expected = state.new_story()
    assert result == expected
