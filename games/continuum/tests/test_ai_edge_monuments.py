"""Edge-case tests for monuments.py."""

import monuments


def test_kind_of_returns_star_for_unknown_or_missing_ids():
    """Unknown achievement ids, empty strings, and None all fall back to 'star'."""
    assert monuments.kind_of("nonexistent") == "star"
    assert monuments.kind_of("") == "star"
    assert monuments.kind_of(None) == "star"


def test_caption_returns_default_for_unknown_kinds():
    """Unknown era kinds, empty strings, and None all fall back to 'Any era'."""
    assert monuments.caption("unknown_era") == "Any era"
    assert monuments.caption("") == "Any era"
    assert monuments.caption(None) == "Any era"


def test_sort_key_pushes_unknown_achievements_to_the_end():
    """Unknown achievement ids get the maximum index, placing them after all known eras."""
    unknown_idx = monuments.sort_key("unknown_id", 0)[0]
    assert unknown_idx == len(monuments.KIND_ORDER) - 1
    # Known achievements get their correct era index
    agrarian_idx = monuments.sort_key("reached_agrarian", 0)[0]
    assert agrarian_idx == monuments.KIND_ORDER.index("agrarian")


def test_sort_key_passes_through_extreme_catalog_indices():
    """The function does not clamp catalog_index; it passes whatever is given."""
    assert monuments.sort_key("reached_agrarian", -100) == (monuments.KIND_ORDER.index("agrarian"), -100)
    assert monuments.sort_key("reached_agrarian", 9999) == (monuments.KIND_ORDER.index("agrarian"), 9999)


def test_icon_svg_draws_star_shape_for_unknown_kinds():
    """Unknown kinds fall back to the star shape and render correctly."""
    svg = monuments.icon_svg("unknown_kind", True)
    assert svg.startswith("<svg")
    assert "monument-svg--earned" in svg
    assert "<rect class=\"m-plinth\"" in svg


def test_icon_svg_treats_falsy_and_truthy_values_for_earned():
    """The earned parameter uses standard truthiness: 0/None/False -> locked, others -> earned."""
    assert "monument-svg--locked" in monuments.icon_svg("tribal", False)
    assert "monument-svg--locked" in monuments.icon_svg("tribal", 0)
    assert "monument-svg--locked" in monuments.icon_svg("tribal", None)
    assert "monument-svg--earned" in monuments.icon_svg("tribal", True)
    assert "monument-svg--earned" in monuments.icon_svg("tribal", 1)
    assert "monument-svg--earned" in monuments.icon_svg("tribal", -1)
