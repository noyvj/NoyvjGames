"""Things in the room are told apart by shape and label, never colour alone; states have non-colour cues; both themes keep
readable contrast. Static checks over style.css, render.py and app.js."""

import re
from pathlib import Path

import render
import rooms

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
        assert _ratio(_var("bad", theme), _var("panel", theme)) >= 3, theme


def test_things_in_the_room_stand_out_from_the_floor_in_both_themes():
    for theme in ("dark", "light"):
        floor = _var("floor-a", theme)
        for name in ("part", "socket", "exit-ring", "robot", "door"):
            assert _ratio(_var(name, theme), floor) >= 3, (theme, name)
        assert _ratio(_var("lamp-on", theme), _var("lamp-off", theme)) >= 3, theme
        assert _ratio(_var("text", theme), _var("surface", theme)) >= 4.5, theme


def test_every_kind_of_thing_has_its_own_shape_and_a_label():
    svg = render.room_svg(rooms.BY_ID["the-shaft"].layout)
    for cls in ("rs-part-body", "rs-socket-frame", "rs-switch-plate", "rs-door-bar", "rs-wall-x", "rs-exit-ring"):
        assert cls in svg
    assert ">EXIT<" in svg and ">1<" in svg and ">A<" in svg
    assert "stroke-dasharray" in CSS and ".rs-door.open .rs-door-bar { display: none; }" in CSS


def test_a_lit_switch_and_a_filled_socket_change_shape_not_only_colour():
    assert ".rs-switch.lit .rs-switch-plate { stroke: var(--lamp-on); stroke-width: 3.5; }" in CSS
    assert ".rs-fill.on { display: inline; }" in CSS


def test_medals_are_words_with_distinct_borders():
    assert ".medal-silver { color: var(--silver); border-style: double" in CSS and ".medal-bronze { color: var(--bronze); border-style: dashed; }" in CSS
    assert "name.charAt(0).toUpperCase() + name.slice(1)" in APP


def test_goal_state_has_a_glyph_and_a_word():
    assert 'content: "\\2713\\00a0"' in CSS and '(done)' in APP


def test_running_and_stopped_steps_differ_by_outline_style():
    assert ".node.running { outline: 3px solid" in CSS and ".node.stopped { outline: 3px dashed" in CSS


def test_the_page_has_the_blanket_hidden_rule_and_reduced_motion_support():
    assert "[hidden] { display: none !important; }" in CSS
    assert 'html[data-reduced-motion="true"]' in CSS and 'html[data-effects="off"]' in CSS
    assert "speedMs" in APP and "data-reduced-motion" in APP


def test_every_list_control_has_a_text_label_for_screen_readers():
    for needle in ('setAttribute("aria-label", "Condition")', "aria-label", "Remove ", "Move ", "Fewer repeats", "More repeats"):
        assert needle in APP
    assert 'class="sr-only"' in HTML and 'aria-live="polite"' in HTML


def test_the_sandbox_can_be_painted_without_a_pointer():
    for needle in ('id="sbx-col"', 'id="sbx-row"', 'id="sbx-paint-button"'):
        assert needle in HTML


def test_skip_link_and_landmarks():
    assert 'class="skip-link" href="#room-panel"' in HTML and 'id="room-panel"' in HTML and "<main" in HTML


def test_touch_targets_are_covered_by_the_shared_sheet():
    assert "shared/touch-targets.css" in HTML
