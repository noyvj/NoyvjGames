"""R4-DRMO-3 wiring checks: the pinned Advance Round button and its strain ring.

These compare the three places that must agree (game.py writes the strain class, ui.js reads it and
sets data-strain, style.css draws the ring for those values) and that the phone rules sit inside the
narrow-screen media block so the Desktop layout is untouched."""
import re
from pathlib import Path


GAME_DIR = Path(__file__).resolve().parent.parent
HTML = (GAME_DIR / "index.html").read_text()
CSS = (GAME_DIR / "style.css").read_text()
JS = (GAME_DIR / "ui.js").read_text()


def phone_block():
    start = CSS.index("R4-DRMO-3")
    media = CSS.index("@media (max-width: 600px) {", start)
    # the block ends at the next top-level comment that opens another feature
    end = CSS.find("/* R4-DRMO-2", media)
    return CSS[media:end if end != -1 else len(CSS)]


def test_button_sits_inside_its_wrap():
    assert re.search(r'<div id="advance-round-wrap">\s*<button id="advance-round-button"', HTML)


def test_ring_values_match_the_engine_levels(game_env):
    levels = [label for _, label in game_env.module.STRAIN_LEVEL_THRESHOLDS]
    assert levels == ["stable", "strained", "critical"]
    for level in ("strained", "critical"):
        assert f'#advance-round-button[data-strain="{level}"]::before' in phone_block()
        assert f'strain--{level}' in JS
    assert 'btn.setAttribute("data-strain", level)' in JS


def test_pinned_button_rules_are_phone_only():
    base = CSS[:CSS.index("R4-DRMO-3")]
    assert "#advance-round-wrap" not in base
    block = phone_block()
    assert "position: fixed" in block
    assert "backdrop-filter: none" in block


def test_ring_animation_is_switched_off_for_reduced_motion():
    block = phone_block()
    assert "prefers-reduced-motion: reduce" in block
    assert "animation: none" in block
