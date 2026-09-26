"""Y11b (planning/TODO.md): light-theme polish for Le Champ de Mots' four visual styles.

Static checks on the stylesheet -- the contrast scan itself was a live,
computed-style WCAG pass in a real browser (see CLAUDE.md's "Y11b" section).
What these pin: the polish rules exist, and every one of them is scoped
under html[data-theme="light"] so the default dark theme is untouched.
"""

import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent


def _light_region():
    css = (GAME_DIR / "visual-styles.css").read_text(encoding="utf-8")
    start = css.rindex("/*", 0, css.index("Y11b LIGHT THEME (2026-09-27), part 1"))
    lowpoly = css.rindex("/*", 0, css.index("LOW-POLY --"))
    part2 = css.rindex("/*", 0, css.index("Y11b LIGHT THEME, part 2"))
    # part 1 (shared + default look) and part 2 (the three alternate styles)
    return css[start:lowpoly] + css[part2:]


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
    assert len(_selectors(_light_region())) >= 60


def test_every_polish_rule_is_scoped_to_the_light_theme():
    for selector in _selectors(_light_region()):
        assert selector.startswith('html[data-theme="light"]'), selector


def test_key_selectors_from_the_scan_are_covered():
    region = _light_region()
    for needle in ['.row', '.minigame-panel', '.tagline', '.shop-rush-patience-fill', '[data-visual-style="lowpoly"]', '[data-visual-style="textbased"]', '[data-visual-style="cartoon"]']:
        assert needle in region, needle


def test_each_alternate_style_has_its_own_light_palette_for_the_main_surfaces():
    css = (GAME_DIR / "visual-styles.css").read_text(encoding="utf-8")
    part2 = css[css.index("Y11b LIGHT THEME, part 2"):]
    for style in ("lowpoly", "textbased", "cartoon"):
        prefix = f'html[data-theme="light"][data-visual-style="{style}"]'
        for target in (" body", " h1", " .section", " .row", " .primary"):
            assert prefix + target in part2, (style, target)
