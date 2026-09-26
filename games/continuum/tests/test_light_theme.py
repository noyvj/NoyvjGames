"""Light theme polish (Y11b): static checks that Continuum's own light rules
exist and stay scoped to the light theme, that the theme control lives in the
Settings panel (the floating pill is retired for this game), and that the 3D
layer re-lights on a theme change without touching dark mode's numbers.

render3d.js / hamlet.js cannot run in this harness (no WebGL), so those are
read as text; the contrast figures and the live scene check are in CLAUDE.md
("Light theme (Y11b)") and were made with a computed-style scan in a browser."""

import json
import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
CSS = (GAME_DIR / "style.css").read_text(encoding="utf-8")
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")
RENDER3D = (GAME_DIR / "render3d.js").read_text(encoding="utf-8")
HAMLET = (GAME_DIR / "hamlet.js").read_text(encoding="utf-8")

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
    assert len(list(_rules(_light_block()))) >= 60


def test_every_light_rule_is_scoped_to_the_light_theme():
    """Dark stays the default: no selector after the banner may apply without
    html[data-theme="light"]."""
    for selector, _body in _rules(_light_block()):
        for part in selector.split(","):
            assert part.strip().startswith(LIGHT), f"unscoped light rule: {part.strip()}"


def test_flagged_areas_have_light_rules():
    block = _light_block()
    for needle in (
        ".row-count",  # dark recessed readout
        ".component-line",
        ".info-toggle summary",  # pale gold on white
        ".research-disclosure > summary",  # consulting mode / challenges gold text
        ".scenario-button.selected",  # selected consulting case / scenario
        ".meter-fill--land",
        ".meter-fill--score",
        ".visual3d-container",  # the 3D sky
        "#game.hamlet-on .visual-stage",
        ".hamlet-main",
        ".hamlet-town-panel",
        ".hamlet-chip button:focus-visible",  # white ring would vanish
        ".real-world-note",
        ".map-glyph",
        ".flow-ribbon--tools",
        ".trajectory-line--mine",
        ".views-dash-row",
    ):
        assert needle in block, f"missing light rule for {needle}"


def test_no_dark_rule_was_changed_by_the_light_pass():
    """A few default (dark) values that the light rules override."""
    assert re.search(r"\.meter-fill--land \{\s*background: #6f9c5a;", CSS)
    assert re.search(r"\.visual3d-container \{[^}]*background: #14101c;", CSS)
    assert re.search(r"\.hamlet-main \{[^}]*color: #f6ecd9;", CSS)
    assert "rgba(4, 3, 2, 0.68)" in CSS


def test_dark_3d_lighting_numbers_are_unchanged():
    assert "0.9 * brightnessFactor * hemiBoost" in RENDER3D
    assert "0.75 * brightnessFactor * sunBoost" in RENDER3D
    # the boosts only change when the light theme is on
    assert re.search(r"let hemiBoost = 1\.0;\s*let sunBoost = 1\.0;\s*if \(isLightTheme\(\)\)", RENDER3D)


def test_scene_reads_the_theme_and_relights_on_change():
    assert 'getAttribute("data-theme")' in RENDER3D
    assert '"noyvj-theme-change"' in RENDER3D
    assert "renderScene(lastVisualState)" in RENDER3D
    assert "isLight: isLightTheme" in RENDER3D


def test_hamlet_rim_follows_the_theme():
    assert "api().isLight" in HAMLET
    assert '"L|"' in HAMLET  # part of the rebuild key, so a theme flip rebuilds the rim


def test_theme_pill_is_retired_for_continuum():
    assert "data-floating-toggle" not in HTML
    assert "../../shared/theme.js" in HTML
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


def test_theme_control_does_not_break_the_settings_reset():
    """Reset to Default is for text size / motion; it must not know about the
    theme (which is a per-device choice managed by shared/theme.js)."""
    settings_js = (GAME_DIR / "settings.js").read_text(encoding="utf-8")
    assert "theme" not in settings_js.lower()


def test_changelog_records_the_light_theme_pass():
    entries = json.loads((GAME_DIR / "changelog.json").read_text(encoding="utf-8"))
    assert any(e["date"] == "2026-09-27" and "light" in e["entry"].lower() for e in entries)
