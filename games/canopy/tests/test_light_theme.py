"""Light theme polish (Y11b): static checks that Canopy's own light rules
exist, stay scoped to the light theme, and that the theme control lives in the
Settings panel (the floating pill is retired for this game).

These read style.css / index.html as text; the contrast numbers themselves were
verified with a live computed-style scan (see CLAUDE.md, "Light theme")."""

import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
CSS = (GAME_DIR / "style.css").read_text(encoding="utf-8")
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")

LIGHT = 'html[data-theme="light"]'


def _light_block():
    """Everything from the Y11b banner comment onward (the light section)."""
    start = CSS.index("Light theme (Y11b")
    return re.sub(r"/\*.*?\*/", "", CSS[CSS.index("*/", start) + 2:], flags=re.S)


def _rules(css):
    """Yield (selector_text, body) for each top-level rule in `css`."""
    for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        yield match.group(1).strip(), match.group(2)


def test_light_section_exists():
    assert "Light theme (Y11b" in CSS
    assert len(list(_rules(_light_block()))) >= 30


def test_every_light_rule_is_scoped_to_the_light_theme():
    """Dark stays the default: no selector in the light section may apply
    without html[data-theme="light"] (bar the settings-row layout rule for the
    theme button, which is layout only and theme independent)."""
    for selector, _body in _rules(_light_block()):
        if selector == ".settings-row #theme-toggle":
            continue
        for part in selector.split(","):
            assert part.strip().startswith(LIGHT), f"unscoped light rule: {part.strip()}"


def test_flagged_areas_have_light_rules():
    block = _light_block()
    for needle in (
        ".selected-plot-state",  # dark recessed readout
        ".income-display",
        ".legend-item",  # dark nameplate
        ".plot-tile.plot-selected",  # pale selection outline
        ".plot-tile.plot-fully-mature",  # pale gold ring
        ".plot-tile.plot-last-hovered",
        ".plot-tile.plot-flood-risk",  # pale blue dashes
        ".value-pop",
        ".info-toggle summary",
        "button.secondary::after",  # status LED
        ".feedback-buttons .secondary.selected",
        ".session-sparkline polyline",
        ".real-world-note",
        ".section.stakeholder-panel",
    ):
        assert needle in block, f"missing light rule for {needle}"


def test_plot_state_fills_are_not_overridden_in_light_theme():
    """Tile fill colours carry the state (with pattern + icon); the light
    rules must not re-paint them."""
    for selector, body in _rules(_light_block()):
        if ".plot-preserved" in selector or ".plot-bare" in selector or ".plot-recovered" in selector \
                or ".plot-replanting" in selector:
            assert "background" not in body, selector


def test_dark_plot_tile_rules_are_unchanged():
    """The default (dark) tile edge and selection colours are still there."""
    assert re.search(r"\.plot-tile \{[^}]*rgba\(140, 160, 255, 0\.16\)", CSS)
    assert re.search(r"\.plot-tile\.plot-selected \{\s*outline: 2px solid #e8e9f0;", CSS)


def test_theme_pill_is_retired_for_canopy():
    assert "data-floating-toggle" not in HTML
    assert '../../shared/theme.js' in HTML
    assert "../../shared/theme-light-games.css" in HTML


def test_settings_panel_hosts_the_theme_control():
    panel = re.search(r'<div id="settings-panel".*?\n    </div>', HTML, flags=re.S)
    assert panel, "settings panel not found"
    body = panel.group(0)
    assert 'id="theme-toggle"' in body
    assert 'class="secondary"' in body.split('id="theme-toggle"')[1].split(">")[0]
    assert "Theme" in body
    # exactly one theme control on the page, so theme.js wires a single button
    assert HTML.count('id="theme-toggle"') == 1
