"""Lines are told apart by shape and letter, never colour alone; states have non-colour cues; both themes keep readable
contrast. Static checks over style.css, render.py and app.js."""

import re
from pathlib import Path

import render
import rules

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
        assert _ratio(_var("accent", theme), _var("panel", theme)) >= 4.5, theme
        assert _ratio(_var("focus", theme), _var("panel", theme)) >= 3, theme
        assert _ratio(_var("on-primary", theme), _var("btn-primary", theme)) >= 4.5, theme
        assert _ratio(_var("text", theme), _var("btn", theme)) >= 4.5, theme
        assert _ratio(_var("ok", theme), _var("panel", theme)) >= 3, theme
        assert _ratio(_var("text", theme), _var("surface", theme)) >= 4.5, theme


def test_every_line_colour_stands_out_from_the_floor_and_its_letter_is_readable_in_both_themes():
    for theme in ("dark", "light"):
        for c in rules.LINES:
            colour = _var("line-" + c, theme)
            for floor in ("floor-a", "floor-a2", "floor-b", "floor-b2"):
                assert _ratio(colour, _var(floor, theme)) >= 3, (theme, c, floor)
            assert _ratio(colour, _var("on-line", theme)) >= 3, (theme, c, "letter on the solid source port")
            assert _ratio(colour, _var("surface", theme)) >= 3, (theme, c, "ring and letter on the sink port")


def test_every_kind_of_thing_has_its_own_shape_and_a_label():
    b = rules.Board({"id": "t", "rows": ["C.#=c", "A.1.B", ".>...", ".....", "....."], "mixers": {"1": "AB"}})
    svg = render.board_svg(b)
    for cls in ("hr-hole-body", "hr-bridge-rail", "hr-valve-arrow", "hr-mixer-body", "hr-port-letter"):
        assert cls in svg
    assert ".hr-dst .hr-shape { fill: var(--surface); stroke: var(--lc); stroke-width: 4.5; }" in CSS
    assert ".hr-src .hr-shape { fill: var(--lc);" in CSS
    assert "stroke-dasharray" in CSS and len(set(render.DASHES.values())) == 8


def test_a_joined_line_and_a_finished_room_say_so_in_words_and_marks():
    assert 'content: "\\2713\\00a0"' in CSS and "joined" in APP
    assert ".result-card.restored { border-style: double" in CSS and ".result-card.patched { border-style: dashed; }" in CSS
    assert ".room-btn.s1 { border-style: dashed" in CSS and ".room-btn.s2 { border-style: double" in CSS


def test_the_page_has_the_blanket_hidden_rule_and_reduced_motion_support():
    assert "[hidden] { display: none !important; }" in CSS
    assert 'html[data-reduced-motion="true"]' in CSS and 'html[data-effects="off"]' in CSS and 'html[data-dots="off"]' in CSS


def test_the_board_can_be_drawn_without_a_pointer():
    for needle in ("onBoardKey", "ArrowUp", "Enter", "Backspace", "Escape"):
        assert needle in APP
    assert 'id="board-holder" class="board-holder" tabindex="0"' in HTML and "aria-label" in HTML


def test_touch_drawing_is_not_stolen_by_scrolling():
    assert "touch-action: none" in CSS and "setPointerCapture" in APP and "pointercancel" in APP


def test_skip_link_landmarks_and_live_regions():
    assert 'class="skip-link" href="#board-panel"' in HTML and 'id="board-panel"' in HTML and "<main" in HTML
    assert 'class="sr-only"' in HTML and 'aria-live="polite"' in HTML
    assert "shared/touch-targets.css" in HTML


def test_every_line_chip_has_a_text_label_for_screen_readers():
    for needle in ('setAttribute("aria-label"', "Press to clear this line", 'b.setAttribute("aria-label", r.number'):
        assert needle in APP
