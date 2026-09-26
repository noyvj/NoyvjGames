"""Y11b (planning/TODO.md): light-theme polish for Aftermath.

Static checks on the stylesheet -- the contrast scan itself was a live,
computed-style WCAG pass in a real browser (see CLAUDE.md's "Y11b" section).
What these pin: the polish rules exist, and every one of them is scoped
under html[data-theme="light"] so the default dark theme is untouched.
"""

import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent


def _light_region():
    css = (GAME_DIR / "style.css").read_text(encoding="utf-8")
    return css[css.rindex("/*", 0, css.index('Y11b light-theme polish (2026-09-27)')):]


def _selectors(css):
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    out = []
    for chunk in css.split("}"):
        if "{" not in chunk:
            continue
        head = chunk.split("{", 1)[0]
        out.extend(part.strip() for part in head.split(",") if part.strip())
    return out


def test_polish_block_exists_and_is_not_empty():
    assert len(_selectors(_light_region())) >= 10


def test_every_polish_rule_is_scoped_to_the_light_theme():
    for selector in _selectors(_light_region()):
        assert selector.startswith('html[data-theme="light"]'), selector


def test_key_selectors_from_the_scan_are_covered():
    region = _light_region()
    for needle in ['#resources-display', '#knowledge-points-display', 'button.primary', '.event-category--weather', '.event-category--non-weather', '.event-category--social', '.skill-practice']:
        assert needle in region, needle
