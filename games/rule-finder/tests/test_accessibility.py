"""Answers are words and marks as well as colour; states have non-colour cues; both themes keep readable contrast. Static checks over
style.css and app.js."""

import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
CSS = (GAME_DIR / "style.css").read_text(encoding="utf-8")
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")


def _var(name, theme="dark"):
    block = CSS.split(":root {")[1].split("}")[0] if theme == "dark" else CSS.split('html[data-theme="light"] {')[1].split("}")[0]
    found = re.search(rf"--{name}:\s*(#[0-9a-fA-F]{{6}})", block)
    if found:
        return found.group(1)
    return _var(name, "dark") if theme == "light" else None


def _lum(hex_color):
    channels = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _ratio(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def test_text_and_controls_keep_contrast_in_both_themes():
    for theme in ("dark", "light"):
        assert _ratio(_var("text", theme), _var("panel", theme)) >= 7, theme
        assert _ratio(_var("muted", theme), _var("panel", theme)) >= 4.5, theme
        assert _ratio(_var("muted", theme), _var("surface", theme)) >= 4.5, theme
        assert _ratio(_var("accent", theme), _var("panel", theme)) >= 4.5, theme
        assert _ratio(_var("focus", theme), _var("panel", theme)) >= 3, theme
        assert _ratio(_var("on-primary", theme), _var("btn-primary", theme)) >= 4.5, theme
        assert _ratio(_var("text", theme), _var("btn", theme)) >= 4.5, theme
        assert _ratio(_var("text", theme), _var("surface", theme)) >= 4.5, theme


def test_the_two_answers_and_the_medals_are_readable_text_and_their_borders_stand_out_in_both_themes():
    for theme in ("dark", "light"):
        for name in ("through", "stopped", "ok", "bad"):
            assert _ratio(_var(name, theme), _var("surface", theme)) >= 4.5, (theme, name)
            assert _ratio(_var(name, theme), _var("panel", theme)) >= 4.5, (theme, name)
        for name in ("gold", "silver", "bronze"):
            assert _ratio(_var(name, theme), _var("surface", theme)) >= 3, (theme, name)
        for shape in ("shape-c", "shape-s", "shape-t", "shape-d", "cell-on"):
            assert _ratio(_var(shape, theme), _var("tile", theme)) >= 3, (theme, shape)
        assert _ratio(_var("text", theme), _var("tile", theme)) >= 7, theme
        assert _ratio(_var("tile-edge", theme), _var("panel", theme)) >= 3, theme


def test_an_answer_is_a_word_and_a_mark_never_colour_alone():
    assert '" \u2713"' in APP and '" \u2715"' in APP and '" goes "' in APP
    assert 'content: "\\2713\\00a0"' in CSS and 'content: "\\2715\\00a0"' in CSS
    assert ".bin-through { border-style: solid;" in CSS and ".bin-stopped { border-style: dashed;" in CSS
    assert ".verdict-card.named { border-style: double;" in CSS and ".verdict-card.near, .verdict-card.conflict { border-style: dashed;" in CSS
    assert ".medal.gold { border-color: var(--gold); color: var(--gold); border-style: double;" in CSS and "Gold" in APP and "Silver" in APP and "Bronze" in APP
    assert ".room-btn.s1 { border-style: double" in CSS


def test_shapes_differ_in_outline_and_size_and_have_names():
    for name in ("circle", "square", "triangle", "diamond"):
        assert name in APP
    for cls in ("sh-c", "sh-s", "sh-t", "sh-d"):
        assert cls in APP and "." + cls in CSS
    assert "<circle" in APP and "<rect" in APP and "<polygon" in APP and 'role="img"' in APP and "aria-label" in APP


def test_the_page_has_the_blanket_hidden_rule_and_reduced_motion_support():
    assert "[hidden] { display: none !important; }" in CSS
    assert 'html[data-reduced-motion="true"]' in CSS and 'html[data-effects="off"]' in CSS
    assert "prefers-reduced-motion" not in CSS or "data-reduced-motion" in CSS


def test_skip_link_landmarks_and_live_regions():
    assert 'class="skip-link" href="#case-panel"' in HTML and 'id="case-panel"' in HTML and "<main" in HTML
    assert 'class="sr-only"' in HTML and 'aria-live="polite"' in HTML and 'id="gate-line"' in HTML
    assert "shared/touch-targets.css" in HTML and "<title>" in HTML and 'lang="en"' in HTML


def test_every_control_has_a_name_for_screen_readers():
    assert 'aria-label="Add a "' not in APP and 'setAttribute("aria-label", "Add a " + SHAPE_NAMES[letter])' in APP
    assert 'setAttribute("aria-pressed"' in APP and "Property for clause" in APP and "Remove clause" in APP
    assert '<label for="num-input">' in HTML and 'role="img"' in HTML
