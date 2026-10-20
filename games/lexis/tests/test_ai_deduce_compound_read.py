
from compound import COMPONENTS, Item
from deduce_compound import Reading, read

# Built directly from the game's data so tests never drift from reality
TRUE_READING = Reading(
    "root_first",
    tuple((letter, meaning) for letter, (meaning, _) in COMPONENTS.items())
)


def test_read_valid_glyph_returns_item():
    """Normal case: a valid two-letter glyph produces an Item."""
    result = read(TRUE_READING, "ko")
    assert isinstance(result, Item)
    assert result.root == "water" and result.size == "small"


def test_read_size_first_order_reverses_slots():
    """Normal case: size_first reading swaps the meaning slots correctly."""
    size_first_reading = Reading("size_first", TRUE_READING.meanings)
    # For "ok", first='o' (small), second='k' (water). With size_first, root=second(water), size=first(small).
    result = read(size_first_reading, "ok")
    assert isinstance(result, Item)
    assert result.root == "water" and result.size == "small"


def test_read_invalid_length_returns_none():
    """Edge case: glyphs that are not exactly two characters cannot be read."""
    assert read(TRUE_READING, "k") is None
    assert read(TRUE_READING, "kou") is None
