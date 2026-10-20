"""Tests for charts.ensure_chapter()."""


import charts

# Save original state
_ORIGINAL_CHARTS = dict(charts.CHARTS)
_ORIGINAL_LOADED = [c["loaded"] for c in charts.CHAPTERS]
_ORIGINAL_MODULES = [c["module"] for c in charts.CHAPTERS]


def reset_charts_state():
    """Reset charts state to original."""
    charts.CHARTS.clear()
    charts.CHARTS.update(_ORIGINAL_CHARTS)
    for chapter, loaded in zip(charts.CHAPTERS, _ORIGINAL_LOADED):
        chapter["loaded"] = loaded
    for chapter, module in zip(charts.CHAPTERS, _ORIGINAL_MODULES):
        chapter["module"] = module


def test_ensure_chapter_returns_true_for_already_loaded_chapter():
    """ensure_chapter() returns True when chapter is already loaded."""
    # Chapter "open" is loaded at module level
    assert charts.ensure_chapter("open") is True


def test_ensure_chapter_returns_false_for_unknown_chapter():
    """ensure_chapter() returns False for unknown chapter id."""
    assert charts.ensure_chapter("unknown") is False
