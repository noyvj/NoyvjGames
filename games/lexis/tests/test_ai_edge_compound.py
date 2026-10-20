"""Edge-case tests for compound.py."""

import pytest
from compound import read_glyph, Tray, react, describe_tray, all_valid_glyphs, GlyphError
from compound import COMPONENTS


def test_read_glyph_empty_string():
    """read_glyph raises GlyphError for an empty string."""
    with pytest.raises(GlyphError) as exc_info:
        read_glyph("")
    assert exc_info.value.reason == "silence"


def test_read_glyph_invalid_characters():
    """read_glyph raises GlyphError when a character is not in COMPONENTS."""
    with pytest.raises(GlyphError) as exc_info:
        read_glyph("xy")
    assert exc_info.value.reason == "unknown_part"


def test_read_glyph_wrong_order():
    """read_glyph raises GlyphError for size-then-root order."""
    root = list(COMPONENTS.keys())[0]
    size = [c for c, (_, slot) in COMPONENTS.items() if slot == "size"][0]
    with pytest.raises(GlyphError) as exc_info:
        read_glyph(size + root)
    assert exc_info.value.reason == "order"


def test_react_empty_tray():
    """react handles a valid glyph on an empty tray."""
    tray = Tray()
    valid_glyph = all_valid_glyphs()[0]
    reaction = react(valid_glyph, tray)
    assert reaction.understood is True
    assert len(reaction.tray.items) == 1


def test_react_full_tray_clamping():
    """react drops the oldest item when the tray exceeds MAX_TRAY."""
    from compound import MAX_TRAY
    tray = Tray()
    valid_glyph = all_valid_glyphs()[0]
    for _ in range(MAX_TRAY + 1):
        reaction = react(valid_glyph, tray)
        tray = reaction.tray
    assert len(tray.items) == MAX_TRAY


def test_describe_tray_empty():
    """describe_tray returns the correct message for an empty tray."""
    tray = Tray()
    assert describe_tray(tray) == "The tray is empty."


def test_all_valid_glyphs_count():
    """all_valid_glyphs returns exactly roots * sizes combinations."""
    glyphs = all_valid_glyphs()
    expected_count = len([c for c, (_, slot) in COMPONENTS.items() if slot == "root"]) * \
        len([c for c, (_, slot) in COMPONENTS.items() if slot == "size"])
    assert len(glyphs) == expected_count
