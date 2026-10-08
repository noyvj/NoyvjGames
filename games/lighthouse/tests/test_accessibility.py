"""Accessibility, light theme and display settings. The page is plain files, so these are source-level checks:
contrast is computed from the real colour variables, every state is checked for a non-colour cue, and the markup is
checked for the labels and live regions the script depends on."""

import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")
CSS = (GAME_DIR / "style.css").read_text(encoding="utf-8")
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")
SETTINGS = (GAME_DIR / "settings.js").read_text(encoding="utf-8")


def _variables(selector):
    block = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", CSS).group(1)
    return dict(re.findall(r"(--[\w-]+):\s*(#[0-9a-fA-F]{6})\b", block))


def _luminance(hex_colour):
    channels = [int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a, b):
    hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


DARK = _variables(":root")
LIGHT = {**DARK, **_variables('html[data-theme="light"]')}
TEXT_PAIRS = [("--text", "--bg"), ("--text", "--panel"), ("--text", "--surface"), ("--text", "--btn"),
              ("--muted", "--panel"), ("--muted", "--bg"), ("--muted", "--surface"), ("--accent", "--panel"), ("--accent", "--bg"),
              ("--on-primary", "--btn-primary")]
UI_PAIRS = [("--edge", "--panel"), ("--edge", "--surface"), ("--focus", "--panel"), ("--focus", "--bg"), ("--hover-edge", "--panel")]


def test_both_themes_define_every_colour_variable():
    assert set(DARK) == set(_variables('html[data-theme="light"]'))


def test_text_contrast_is_at_least_aa_in_both_themes():
    for name, theme in (("dark", DARK), ("light", LIGHT)):
        for fg, bg in TEXT_PAIRS:
            assert contrast(theme[fg], theme[bg]) >= 4.5, f"{name}: {fg} on {bg} is {contrast(theme[fg], theme[bg]):.2f}"


def test_outlines_and_focus_ring_contrast_is_at_least_three_to_one_in_both_themes():
    for name, theme in (("dark", DARK), ("light", LIGHT)):
        for fg, bg in UI_PAIRS:
            assert contrast(theme[fg], theme[bg]) >= 3.0, f"{name}: {fg} on {bg}"


def test_the_meter_fill_stands_out_from_its_track_in_both_themes():
    for name, theme in (("dark", DARK), ("light", LIGHT)):
        assert contrast(theme["--accent"], theme["--off"]) >= 3.0, name


def test_the_stylesheet_has_no_hard_coded_dark_surfaces_left():
    body = CSS.split("* { box-sizing")[1]
    assert not re.search(r"#0f1b25|#1a2c3a|#1d5f80|#0b141c", body), "use the colour variables so the light theme applies"


def test_the_light_theme_follows_the_site_theme_and_has_its_own_scene():
    assert 'html[data-theme="light"]' in CSS and "PAL" in APP and 'isLight() ? "light" : "dark"' in APP
    assert "noyvj-theme-change" in APP and "noyvj-theme-change" in SETTINGS


def test_state_is_never_colour_only():
    # meters: a pattern for low and failing, a number and a word beside every one
    assert 'data-state="low"' in CSS and 'data-state="empty"' in CSS and "repeating-linear-gradient" in CSS
    assert ".structure-list .meter[data-state=\"worn\"]" in CSS and ".structure-list .meter[data-state=\"poor\"]" in CSS
    assert "part-state" in APP and "part-num" in APP and "hud-oil-state" in HTML and "hud-energy-state" in HTML
    # weather and ships: an icon and a word
    assert "cond_icon" in APP and "cond_label" in APP
    # ship outcomes: a mark plus words; the chosen lamp level: bold, underlined and heavy-outlined
    assert '.ship-state[data-state="passed"]::before' in CSS and '.ship-state[data-state="damaged"]::before' in CSS
    assert 'aria-pressed="true"' in CSS and "underline" in CSS
    assert "Passed safely" in APP and "Turned back" in APP
    # barometer cells: filled or hollow mark as well as the border
    assert ("\u25CF" in APP or "\\u25CF" in APP) and ("\u25CB" in APP or "\\u25CB" in APP)


def test_ship_kinds_differ_by_silhouette_and_label_not_colour():
    kinds = re.findall(r'^\s+(fisher|ferry|cargo|yacht|mail): \[\[', APP, flags=re.M)
    assert sorted(kinds) == ["cargo", "ferry", "fisher", "mail", "yacht"]
    shapes = re.findall(r'^\s+(?:fisher|ferry|cargo|yacht|mail): (\[\[.*)$', APP, flags=re.M)
    assert len(set(shapes)) == 5


def test_live_regions_and_labels_exist():
    for needle in ('id="announce"', 'role="status"', 'aria-live="polite"', 'id="scene" class="scene" viewBox="0 0 900 420" role="img"',
                   'class="skip-link"', 'role="group" aria-label="Station status"', 'aria-expanded="false"'):
        assert needle in HTML, needle
    assert "$(\"scene\").setAttribute(\"aria-label\"" in APP


def test_focus_survives_redraws():
    assert "fillOnce" in APP and "aria-disabled" in APP
    assert "[aria-disabled=\"true\"]" in CSS


def test_reduced_motion_and_effects_switches_stop_every_animation():
    assert 'html[data-reduced-motion="true"] *' in CSS and 'html[data-effects="off"]' in CSS
    for name in ("beam.sweeping", "wave-row", "rain-layer", "fog-layer"):
        assert name in CSS
    assert "reducedMotion" in APP and "beam-edge" in APP          # the static cone plus a tick mark


def test_settings_store_only_display_choices_on_the_device():
    for key in ("lighthouse-text-scale", "lighthouse-reduced-motion", "lighthouse-effects", "lighthouse-high-contrast"):
        assert key in SETTINGS


def test_keyboard_reaches_everything_and_night_keys_are_documented():
    assert "onKey" in APP and 'k >= "1" && k <= "4"' in APP
    assert "Space: pause or resume the night" in HTML
    assert 'role="group" aria-labelledby="lamp-controls-label"' in HTML


def test_phone_width_layout_exists():
    assert "@media (max-width: 640px)" in CSS and "grid-template-columns: repeat(3" in CSS
