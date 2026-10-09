"""State is told by words, shapes and borders as well as colour; both themes keep readable contrast. Static checks over style.css,
render.py and app.js."""

import re
from pathlib import Path

import render

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
        assert _ratio(_var("accent", theme), _var("surface", theme)) >= 4.5, theme
        assert _ratio(_var("focus", theme), _var("panel", theme)) >= 3, theme
        assert _ratio(_var("on-primary", theme), _var("btn-primary", theme)) >= 4.5, theme
        assert _ratio(_var("text", theme), _var("btn", theme)) >= 4.5, theme
        assert _ratio(_var("text", theme), _var("surface", theme)) >= 4.5, theme
        assert _ratio(_var("ok", theme), _var("panel", theme)) >= 3, theme
        assert _ratio(_var("bad", theme), _var("panel", theme)) >= 3, theme
        assert _ratio(_var("cool", theme), _var("surface", theme)) >= 3, theme
        for seal in ("gold", "silver", "bronze"):
            assert _ratio(_var(seal, theme), _var("panel", theme)) >= 3, (theme, seal)


def test_the_three_seals_are_words_with_distinct_borders():
    assert ".seal-steady { color: var(--silver); border-style: double" in CSS and ".seal-rough { color: var(--bronze); border-style: dashed; }" in CSS
    assert "name.charAt" not in APP and 'el("span", "seal seal-" + name.toLowerCase(), name)' in APP


def test_a_settled_patient_has_a_ring_a_dashed_border_and_the_word():
    assert ".patient.settled { border-style: dashed; }" in CSS
    assert '"Settled"' in APP
    assert "#7dffb2" in render.bust("dov", True) and "#7dffb2" not in render.bust("dov", False)


def test_a_selected_patient_differs_by_border_width_not_only_colour():
    assert '.patient[aria-pressed="true"] { border-color: var(--accent); border-width: 3px;' in CSS and 'setAttribute("aria-pressed"' in APP


def test_scan_readings_differ_by_border_style_and_words():
    for needle in (".readings li.positive { border: 2px solid", ".readings li.clear { border-style: dotted; }", ".readings li.unknown"):
        assert needle in CSS
    assert '"not run"' in APP and "r.positive" in APP


def test_ruled_out_conditions_are_struck_through_as_well_as_dimmed_and_the_setting_can_turn_it_off():
    assert "text-decoration: line-through" in CSS and 'html[data-narrow="off"] .sheet li.ruled-out' in CSS
    assert 'id="narrow-checkbox"' in HTML


def test_shelves_have_letters_and_buttons_that_cannot_be_used_look_dashed_with_a_reason():
    assert ".shelf .letter" in CSS and ".shelf.empty { border-style: dashed;" in CSS
    assert ".act-row button.unavailable { border-style: dashed;" in CSS and "Not available: " in APP


def test_every_supply_letter_is_shown_on_its_button_and_its_shelf():
    assert 'el("span", "letter", i.glyph)' in APP and 'actButton(t.glyph' in APP and 'actButton(x.glyph' in APP


def test_the_page_has_the_blanket_hidden_rule_and_reduced_motion_support():
    assert "[hidden] { display: none !important; }" in CSS
    assert 'html[data-reduced-motion="true"]' in CSS and 'html[data-effects="off"]' in CSS


def test_live_regions_labels_skip_link_and_landmarks():
    assert 'class="sr-only"' in HTML and 'aria-live="polite"' in HTML and "aria-label" in APP
    assert 'class="skip-link" href="#shift-panel"' in HTML and 'id="shift-panel"' in HTML and "<main" in HTML
    assert 'role="group" aria-label="Patients in the ward"' in HTML


def test_portraits_have_a_text_name_for_screen_readers():
    for crew in ("maren", "kit", "orla"):
        assert 'role="img" aria-label=' in render.bust(crew)
    assert 'aria-label="The infirmary at night"' in render.scene(1)


def test_touch_targets_are_covered_by_the_shared_sheet():
    assert "shared/touch-targets.css" in HTML


def test_the_tutorial_only_points_at_things_the_page_has():
    ids = set(re.findall(r'(?<![-\w])id="([^"]+)"', HTML))
    steps = APP.split("var TUTORIAL_STEPS = [")[1].split("];")[0]
    selectors = re.findall(r'selector: "#([\w-]+)"', steps)
    assert len(selectors) >= 5 and set(selectors) <= ids
    assert 'id="tutorial-restart-button"' in HTML and "stationMedicTutorialSteps" in HTML and "tutorial.js" in HTML


def test_destructive_actions_ask_first():
    assert 'askThen("station-medic-reset"' in APP and 'askThen("station-medic-restore"' in APP and 'askThen("station-medic-comfort"' in APP
