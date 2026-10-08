"""Goods are told apart by shape, letter and tier number, never by colour alone; states have non-colour cues; both
themes keep readable contrast. Static checks over style.css and the engine's own tables."""

import re
from pathlib import Path

import goods

GAME_DIR = Path(__file__).resolve().parent.parent
CSS = (GAME_DIR / "style.css").read_text(encoding="utf-8")


def _var(name, theme="dark"):
    block = CSS.split(':root {')[1].split('}')[0] if theme == "dark" else CSS.split('html[data-theme="light"] {')[1].split('}')[0]
    found = re.search(rf"--{name}:\s*(#[0-9a-fA-F]{{6}})", block)
    return found.group(1) if found else None


def _lum(hex_color):
    channels = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _ratio(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def test_every_family_has_its_own_shape_class_and_a_distinct_letter():
    shapes = {goods.FAMILY_INFO[f]["shape"] for f in goods.FAMILIES}
    assert len(shapes) == len(goods.FAMILIES)
    for shape in shapes | {"star"}:
        assert f".shape-{shape} .good-shape" in CSS, shape
    assert len({goods.FAMILY_INFO[f]["letter"] for f in goods.FAMILIES}) == len(goods.FAMILIES)


def test_the_letter_on_every_good_is_readable_in_both_themes():
    ink = _var("ink")
    for fam in list(goods.FAMILIES) + ["wild"]:
        assert _ratio(_var(f"fam-{fam}"), ink) >= 4.5, fam      # the good's colour is a fixed fill in both themes


def test_text_and_muted_text_keep_contrast_on_the_panels_in_both_themes():
    for theme in ("dark", "light"):
        assert _ratio(_var("text", theme), _var("panel", theme)) >= 7, theme
        assert _ratio(_var("muted", theme), _var("panel", theme)) >= 4.5, theme
        assert _ratio(_var("accent", theme), _var("panel", theme)) >= 4.5, theme
        assert _ratio(_var("focus", theme), _var("panel", theme)) >= 3, theme


def test_selection_and_match_differ_by_outline_style_not_only_colour():
    assert re.search(r"\.cell\.selected\s*\{[^}]*outline:\s*3px solid", CSS)
    assert re.search(r"\.cell\.partner\s*\{[^}]*outline:\s*3px dashed", CSS)
    assert '.cell.partner::after { content: "+"' in CSS


def test_tier_is_shown_as_a_number_and_as_pips():
    app = (GAME_DIR / "app.js").read_text(encoding="utf-8")
    assert "cell.letter + (cell.family" in app and 'el("span", "pip")' in app


def test_the_page_has_the_blanket_hidden_rule_and_reduced_motion_support():
    assert "[hidden] { display: none !important; }" in CSS
    assert 'html[data-reduced-motion="true"]' in CSS and 'html[data-effects="off"]' in CSS


def test_every_cell_button_has_a_text_label():
    app = (GAME_DIR / "app.js").read_text(encoding="utf-8")
    assert 'btn.setAttribute("aria-label", label)' in app and "empty" in app
