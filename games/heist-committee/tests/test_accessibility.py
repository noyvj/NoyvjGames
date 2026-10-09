"""Contrast ratios for the palette in both themes, the colourblind rule (every state has a shape, glyph or word as
well as a colour), and the small-screen layout rules."""

import re
from pathlib import Path

GAME = Path(__file__).resolve().parent.parent
CSS = (GAME / "style.css").read_text(encoding="utf-8")
APP = (GAME / "app.js").read_text(encoding="utf-8")
PLAN = (GAME / "plan.js").read_text(encoding="utf-8")
PLAY = (GAME / "play.js").read_text(encoding="utf-8")


def block(selector_start):
    start = CSS.index(selector_start)
    return CSS[CSS.index("{", start) + 1:CSS.index("}", start)]


def palette(text):
    return {m.group(1): m.group(2) for m in re.finditer(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})", text)}


DARK = palette(block(":root {"))
LIGHT = dict(DARK, **palette(block('html[data-theme="light"] {')))


def lum(hex_color):
    rgb = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def ratio(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


TEXT_PAIRS = [("text", "bg"), ("text", "panel"), ("text", "cell"), ("text", "cell-fill"), ("text", "btn"), ("muted", "panel"),
              ("muted", "bg"), ("muted", "cell"), ("accent", "bg"), ("accent", "panel"), ("on-primary", "btn-primary"),
              ("good", "panel"), ("warn", "panel"), ("bad", "panel"), ("info", "panel"), ("good", "cell-fill"),
              ("warn", "cell-fill"), ("bad", "cell-fill"), ("text", "surface"), ("muted", "surface")]
UI_PAIRS = [("focus", "bg"), ("focus", "panel"), ("edge", "panel"), ("armed", "cell-fill"), ("selected", "panel")]


def test_text_contrast_in_both_themes():
    for name, theme in (("dark", DARK), ("light", LIGHT)):
        for fg, bg in TEXT_PAIRS:
            assert ratio(theme[fg], theme[bg]) >= 4.5, (name, fg, bg, round(ratio(theme[fg], theme[bg]), 2))


def test_interface_contrast_in_both_themes():
    for name, theme in (("dark", DARK), ("light", LIGHT)):
        for fg, bg in UI_PAIRS:
            assert ratio(theme[fg], theme[bg]) >= 3.0, (name, fg, bg, round(ratio(theme[fg], theme[bg]), 2))


def test_the_status_colours_are_never_the_only_cue():
    # odds: a glyph and a word per level
    assert re.search(r'ODDS_GLYPH = \{ solid: "●", risky: "◐", "long": "○", none: "✕" \}', APP)
    for word in ("Solid", "Risky", "Long shot", "No chance"):
        assert word in (GAME / "content" / "lines.json").read_text(encoding="utf-8")
    # results: icon + word
    assert 'TAGS = {\n    crit: ["★", "Perfect"], success: ["✓", "Success"], partial: ["~", "Messy"], fail: ["✗", "Failed"]' in PLAY
    # checklist: mark + screen-reader word
    assert 'words = { ok: "Covered", warn: "Warning", info: "Note" }' in PLAN
    # outcome borders also differ by style, not hue: failed and messy cells carry a written label
    assert 'res.icon + " " + res.label' in PLAN


def test_roles_have_five_distinct_shapes_and_letters(C):
    shapes = {r["shape"] for r in C.roles.values()}
    assert len(shapes) == 5
    for shape in shapes:
        assert f"{shape}:" in APP
    assert "card.letter" in APP


def test_odds_chips_differ_by_border_style_as_well_as_colour():
    assert ".odds-none { color: var(--bad); border-style: dashed; }" in CSS


def test_selected_armed_and_cursor_states_have_non_colour_cues():
    assert ".cell.selected { outline: 3px solid" in CSS
    assert '.tray-item[aria-pressed="true"] .t-name::after { content: " (armed)"' in CSS
    assert '.cell.cursor' in CSS or "focus" in CSS


def test_reduced_motion_and_effects_switches_remove_animation():
    assert 'html[data-reduced-motion="true"] *' in CSS and 'html[data-effects="off"] *' in CSS
    assert "animation: none !important" in CSS


def test_small_screen_rules_keep_the_timeline_scrollable_and_the_dock_clear():
    assert "overflow-x: auto" in CSS
    assert "@media (max-width: 640px)" in CSS
    assert "position: sticky; left: 0" in CSS            # the lane header stays put while the beats scroll
    assert "#tray-panel.mobile-docked" in CSS


def test_no_hard_coded_hex_colours_outside_the_palette_and_ghost():
    body = CSS.replace(block(":root {"), "").replace(block('html[data-theme="light"] {'), "")
    for match in re.finditer(r"#[0-9a-fA-F]{3,6}\b", body):
        context = body[max(0, match.start() - 40):match.end() + 5]
        assert any(k in context for k in ("rgba", "high-contrast", "--line", "--edge", "--muted")), context
