"""R-19: the top-tier seawall gets a faint glint, motion only and reduced-motion safe."""

import pathlib

CSS = (pathlib.Path(__file__).resolve().parent.parent / "style.css").read_text()


def test_the_glint_exists_only_for_the_top_tier_and_only_without_reduced_motion():
    assert "@keyframes tide-barrier-glint" in CSS
    block = CSS[CSS.index("@media (prefers-reduced-motion: no-preference)"):]
    block = block[: block.index("}\n}") + 3] if "}\n}" in block else block[:200]
    assert ".coastline-seawall--t4" in block and "tide-barrier-glint" in block
    assert ".coastline-seawall--t3 {" not in block


def test_the_flourish_touches_no_tile_state_or_colour():
    keyframes = CSS[CSS.index("@keyframes tide-barrier-glint"): CSS.index("@media (prefers-reduced-motion: no-preference)")]
    assert "background" not in keyframes and "opacity" not in keyframes and "transform" not in keyframes


def test_the_manual_reduced_motion_switch_still_collapses_animations():
    assert 'html[data-reduced-motion="true"] *' in CSS and "animation-duration: 0.001ms !important" in CSS
