"""Tests for story.label_ship()."""

import story


class MockKeep:
    """Minimal mock of the keep object used by label_ship."""

    def __init__(self, quiet=False):
        self.quiet = quiet


def test_label_ship_returns_plain_text_when_quiet_mode_is_on():
    """When the keeper's Quiet mode is on, sailor names are never shown."""
    keep = MockKeep(quiet=True)
    ship = {"who": "any_id"}
    text = "Lantern Lark"
    assert story.label_ship(keep, ship, text) == text


def test_label_ship_appends_sailor_name_when_story_is_on_and_sailor_is_known():
    """When the story is on and the ship carries a known sailor, their name is appended."""
    keep = MockKeep(quiet=False)
    # Use a real sailor ID from the game's data to avoid inventing formats.
    known_sid = next(iter(story.lore.SAILORS))
    ship = {"who": known_sid}
    text = "Lantern Lark"
    expected = "%s (%s)" % (text, story.sailor_name(known_sid))
    assert story.label_ship(keep, ship, text) == expected


def test_label_ship_returns_plain_text_when_sailor_is_unknown():
    """When the story is on but the sailor ID is not in lore, it falls back to plain text."""
    keep = MockKeep(quiet=False)
    ship = {"who": "nonexistent_sailor"}
    text = "Lantern Lark"
    assert story.label_ship(keep, ship, text) == text
