"""Non-colour cues, keyboard use, reduced motion, light-theme contrast. Colour is decoration only."""

import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
CSS = (GAME_DIR / "style.css").read_text(encoding="utf-8")
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")


def _vars(block):
    return {k: v.strip() for k, v in re.findall(r"--([a-z-]+):\s*([^;]+);", block)}


def _block(selector):
    m = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", CSS)
    return m.group(1)


DARK = _vars(_block(":root"))
LIGHT = dict(DARK, **_vars(_block('html[data-theme="light"]')))


def _rgb(value):
    value = value.strip()
    m = re.fullmatch(r"#([0-9a-f]{6})", value)
    assert m, value
    h = m.group(1)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _lum(rgb):
    def ch(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a, b):
    la, lb = sorted((_lum(_rgb(a)), _lum(_rgb(b))), reverse=True)
    return (la + 0.05) / (lb + 0.05)


TEXT_PAIRS = [("text", "bg"), ("text", "panel"), ("text", "surface"), ("text", "btn"), ("muted", "panel"), ("muted", "surface"),
              ("muted", "bg"), ("accent-ink", "panel"), ("accent-ink", "surface"), ("accent-ink", "bg"),
              ("on-primary", "btn-primary"), ("banner-text", "banner-bg"), ("accent-ink", "banner-bg")]
EDGE_PAIRS = [("edge", "panel"), ("edge", "surface"), ("focus", "bg"), ("focus", "panel")]


def test_text_contrast_meets_wcag_aa_in_both_themes():
    for name, theme in (("dark", DARK), ("light", LIGHT)):
        for fg, bg in TEXT_PAIRS:
            assert ratio(theme[fg], theme[bg]) >= 4.5, (name, fg, bg, round(ratio(theme[fg], theme[bg]), 2))


def test_outlines_and_focus_rings_meet_3_to_1_in_both_themes():
    for name, theme in (("dark", DARK), ("light", LIGHT)):
        for fg, bg in EDGE_PAIRS:
            assert ratio(theme[fg], theme[bg]) >= 3.0, (name, fg, bg, round(ratio(theme[fg], theme[bg]), 2))


def test_slot_states_differ_by_border_style_and_written_label_not_colour():
    assert re.search(r"\.slot\.right\s*\{[^}]*double", CSS)
    assert re.search(r"\.slot\.wrong\s*\{[^}]*dashed", CSS)
    assert re.search(r"\.slot\.empty\s*\{[^}]*dotted", CSS)
    assert re.search(r"\.slot\.filled\s*\{[^}]*solid", CSS)
    for label in ("✔ Right place (locked)", "✖ Not here yet", "Empty"):
        assert label in APP, label


def test_the_hint_direction_is_written_as_text_and_an_arrow():
    assert "earlier" in APP and "later" in APP and "◀" in APP and "▶" in APP


def test_a_picked_up_card_is_marked_by_a_triangle_and_a_thicker_border_as_well_as_colour():
    rule = re.search(r'\.card\[aria-pressed="true"\]\s*\{([^}]*)\}', CSS).group(1)
    assert "border-width: 4px" in rule
    assert 'content: "\\25B6' in CSS


def test_confidence_levels_have_symbol_label_and_border_style():
    assert re.search(r"\.conf\.disputed\s*\{[^}]*dashed", CSS) and re.search(r"\.conf\.traditional-but-doubtful\s*\{[^}]*dotted", CSS)
    py = (GAME_DIR / "game.py").read_text(encoding="utf-8")
    assert '"Documented", "✔"' in py and '"Disputed", "≈"' in py and '"Traditional but doubtful", "?"' in py


def test_locked_sections_and_archive_entries_say_so_in_words_and_use_dashes():
    assert "Locked: clear" in APP and "Not found yet" in APP
    assert re.search(r"\.tile\.locked\s*\{[^}]*dashed", CSS) and re.search(r'\.section-card\[aria-disabled="true"\]\s*\{[^}]*dashed', CSS)


def test_earned_achievements_are_solid_and_written_unearned_are_dashed():
    assert "Earned" in APP and "Not yet" in APP
    assert re.search(r"\.ach-list li\.earned\s*\{[^}]*solid", CSS) and re.search(r"\.ach-list li:not\(\.earned\)\s*\{[^}]*dashed", CSS)


def test_reduced_motion_and_effects_switches_remove_every_animation():
    assert re.search(r'html\[data-reduced-motion="true"\] \*[^{]*\{[^}]*animation: none !important', CSS)
    assert re.search(r'html\[data-effects="off"\] \*[^{]*\{[^}]*animation: none !important', CSS)
    assert "found-in" in CSS and "scroll-behavior: auto" in CSS


def test_the_html_hidden_attribute_always_wins():
    assert "[hidden] { display: none !important; }" in CSS


def test_keyboard_use_is_complete():
    for key in ('"Escape"', '"Delete"', '"Backspace"', "ArrowRight", "[1-8]"):
        assert key in APP, key
    assert "keydown" in APP and 'type = "button"' in APP
    assert "All five" not in HTML
    assert 'class="skip-link"' in HTML and 'id="puzzle-panel"' in HTML


def test_live_regions_and_labels_exist():
    assert 'id="announce"' in HTML and 'aria-live="polite"' in HTML
    assert 'id="message-line"' in HTML and 'role="status"' in HTML
    assert 'aria-labelledby="report-heading"' in HTML
    assert 'aria-label="Archive completion"' in HTML
    assert "aria-expanded" in HTML and "aria-controls" in HTML
    assert 'for="set-select"' in HTML


def test_focus_ring_is_strong_and_focus_survives_redraws():
    assert "outline: 3px solid var(--focus)" in CSS
    assert "data-fk" in APP and "restoreFocus" in APP


def test_every_button_in_the_static_html_has_a_name():
    for m in re.finditer(r"<button([^>]*)>(.*?)</button>", HTML, re.S):
        attrs, text = m.group(1), re.sub(r"<[^>]+>", "", m.group(2)).strip()
        assert text or "aria-label" in attrs, m.group(0)


def test_text_scale_is_a_variable_and_the_phone_layout_is_one_column():
    assert "calc(100% * var(--text-scale, 1))" in CSS
    assert re.search(r"@media \(max-width: 640px\)\s*\{[^}]*\.slots \{ grid-template-columns: minmax\(0, 1fr\)", CSS)


def test_art_is_drawn_by_code():
    assert "createElementNS" in APP and "<svg" in HTML
    assert "data:image/svg+xml" in HTML          # the favicon is inline SVG, not a file
