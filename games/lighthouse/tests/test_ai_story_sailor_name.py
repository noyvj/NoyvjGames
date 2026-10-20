"""Tests for story.sailor_name()."""

import lore
import pytest
import story


def test_sailor_name_returns_correct_name_for_first_sailor():
    sid = lore.SAILOR_ORDER[0]
    name = story.sailor_name(sid)
    assert name == lore.SAILORS[sid]["name"]
    assert isinstance(name, str) and len(name) > 0


def test_sailor_name_returns_correct_name_for_another_sailor():
    sid = lore.SAILOR_ORDER[1]
    name = story.sailor_name(sid)
    assert name == lore.SAILORS[sid]["name"]


def test_sailor_name_raises_keyerror_for_unknown_id():
    with pytest.raises(KeyError):
        story.sailor_name("nonexistent_sailor")
