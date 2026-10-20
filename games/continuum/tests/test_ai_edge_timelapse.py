"""Edge-case tests for timelapse.py."""

import sim
import timelapse as tl


def test_usable_boundary_values():
    """usable() returns False for fewer than two frames, True otherwise."""
    assert tl.usable([]) is False
    assert tl.usable([{}]) is False
    assert tl.usable([{}, {}]) is True
    assert tl.usable([{}, {}, {}]) is True


def test_caption_with_minimal_and_negative_values():
    """caption() formats correctly even with zero or negative numbers."""
    frame = {"season": 1, "era": "tribal", "population": 0, "score": 0.0, "researched": 0}
    cap = tl.caption(frame)
    assert "Season 1" in cap and "sustainability 0" in cap

    neg_frame = {"season": -5, "era": "tribal", "population": -10, "score": -20.0, "researched": 0}
    cap_neg = tl.caption(neg_frame)
    assert "Season -5" in cap_neg and "sustainability -20" in cap_neg


def test_chart_svg_clamps_index_and_rejects_short_lists():
    """chart_svg() clamps the cursor index and requires at least two frames."""
    frames = [{"season": s, "era": "tribal", "population": 10, "score": 50.0, "food": 0, "land": 0,
               "researched": 0, "buildings": {b: 0 for b in sim.BUILDINGS}} for s in range(1, 4)]

    assert tl.chart_svg([], 0) == ""
    single = [frames[0]]
    assert tl.chart_svg(single, 0) == ""

    svg_neg = tl.chart_svg(frames, -10)
    assert "Cursor at season 1" in svg_neg

    svg_pos = tl.chart_svg(frames, 99)
    assert "Cursor at season 3" in svg_pos


def test_sample_indexes_extreme_counts():
    """sample_indexes() handles zero, one, two, and wanted > count correctly."""
    assert tl.sample_indexes(0) == []
    assert tl.sample_indexes(1) == [0]
    assert tl.sample_indexes(2) == [0, 1]
    assert tl.sample_indexes(3, wanted=10) == [0, 1, 2]


def test_strip_filename_long_and_special_characters():
    """strip_filename() sanitizes long names and replaces non-alphanumeric characters."""
    frames = [{"season": 42}]

    long_name = "A" * 100
    fn_long = tl.strip_filename(long_name, frames)
    assert fn_long.startswith("continuum-") and fn_long.endswith("-timelapse-season-42.svg")

    special_chars = "!@#$%^&*()"
    fn_special = tl.strip_filename(special_chars, frames)
    # All non-alnum become hyphens, stripped from ends, falls back to 'settlement'
    assert fn_special.startswith("continuum-settlement") and fn_special.endswith("-timelapse-season-42.svg")


def test_pins_at_boundary_seasons():
    """pins_at() returns empty lists for seasons outside the pin list range."""
    pins = [{"season": 1, "kind": "era", "text": "x"}, {"season": 5, "kind": "build", "text": "y"}]

    assert tl.pins_at(pins, 0) == []
    assert len(tl.pins_at(pins, 1)) == 1
    assert len(tl.pins_at(pins, 3)) == 0
    assert len(tl.pins_at(pins, 6)) == 0
