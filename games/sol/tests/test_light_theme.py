"""Y11b (planning/TODO.md): light-theme polish for SOL.

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
    assert len(_selectors(_light_region())) >= 15


def test_every_polish_rule_is_scoped_to_the_light_theme():
    for selector in _selectors(_light_region()):
        assert selector.startswith('html[data-theme="light"]'), selector


def test_key_selectors_from_the_scan_are_covered():
    region = _light_region()
    for needle in ['button.priority-option', '.research-tree-node--locked', '.research-node-detail', '#research-status', '.ecology-status', '.cross-summary-label', 'button.secondary.mini-button.selected']:
        assert needle in region, needle


# --- Y11b (d): the theme switch lives in the Settings panel ------------------


def _html():
    return (GAME_DIR / "index.html").read_text(encoding="utf-8")


def test_settings_panel_hosts_the_theme_toggle():
    html = _html()
    panel_start = html.index('id="settings-panel"')
    panel_end = html.index("</div>\n    <details", panel_start)
    panel = html[panel_start:panel_end]
    assert re.search(r'<button id="theme-toggle" class="[^"]*\btheme-toggle\b[^"]*" type="button">', panel)


def test_floating_theme_pill_is_no_longer_requested():
    html = _html()
    tag = re.search(r'<script src="\.\./\.\./shared/theme\.js"[^>]*></script>', html).group(0)
    assert "data-floating-toggle" not in tag


def test_theme_js_script_still_loads_before_the_toggle_exists():
    html = _html()
    assert html.index("shared/theme.js") < html.index('id="theme-toggle"')


def test_shared_theme_js_wires_any_theme_toggle_element():
    # The control has no handler of its own: shared/theme.js finds it by id and
    # class. If that contract ever changes, this test is the early warning.
    js = (GAME_DIR.parent.parent / "shared" / "theme.js").read_text(encoding="utf-8")
    assert '"#theme-toggle, .theme-toggle"' in js
    assert "NoyvjTheme.toggle()" in js


def test_settings_js_does_not_duplicate_the_theme_handler():
    js = (GAME_DIR / "settings.js").read_text(encoding="utf-8")
    assert "theme" not in js.lower()
