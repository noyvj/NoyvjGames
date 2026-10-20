"""Lexis -- edge-case tests for deduce_compound.py."""


from compound import Item, Tray
from compound_scenes import CompoundScene, compound_scenes
from deduce_compound import (
    Reading,
    all_readings,
    consistent_readings,
    determinate,
    disagreements,
    predict,
    read,
)

SCENES = compound_scenes()


def test_read_rejects_invalid_glyph_lengths():
    """read returns None for glyphs that are not exactly two characters."""
    true_reading = next(r for r in all_readings() if r.order == "root_first")
    assert read(true_reading, "") is None
    assert read(true_reading, "k") is None
    assert read(true_reading, "kou") is None


def test_predict_handles_empty_and_full_trays():
    """predict correctly appends to an empty tray and caps a full tray at six items."""
    # all_readings() yields random assignments; construct one that maps 'k'->water, 'o'->small.
    true_reading = Reading("root_first", (("k", "water"), ("o", "small"), ("m", "fire"), ("t", "grain"), ("u", "big")))
    empty_tray = Tray()
    assert predict(true_reading, "ko", empty_tray).items == (Item("water", "small"),)

    full_tray = Tray((Item("water", "small"),) * 6)
    result = predict(true_reading, "mo", full_tray)
    assert len(result.items) == 6
    assert result.items[-1] == Item("fire", "small")


def test_consistent_readings_with_no_scenes_returns_all():
    """With zero scenes, every reading is consistent because all() on an empty iterable is True."""
    readings = consistent_readings([])
    assert len(readings) > 0
    assert all(isinstance(r, type(readings[0])) for r in readings)


def test_disagreements_with_contradictory_scenes_returns_error_tuple():
    """When no reading fits the scenes, disagreements returns a specific error tuple."""
    bad = CompoundScene("bad", "ko", Tray(), Tray((Item("fire", "big"),)))
    result = disagreements((SCENES[0], bad))
    assert len(result) == 1
    assert result[0][0] == "no reading fits these scenes"


def test_determinate_with_empty_scenes_is_false():
    """With no scenes to constrain readings, the language is not determinate."""
    assert not determinate([])
