"""State is told by words, shapes and borders as well as colour; both themes keep readable contrast. Static checks over style.css,
render.py and app.js."""

import re
from pathlib import Path

import lexicon as lx
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
        assert _ratio(_var("text", theme), _var("room-a", theme)) >= 7, theme
        assert _ratio(_var("text", theme), _var("room-b", theme)) >= 7, theme
        assert _ratio(_var("muted", theme), _var("room-b", theme)) >= 4.5, theme
        assert _ratio(_var("ok", theme), _var("panel", theme)) >= 3, theme
        assert _ratio(_var("cool", theme), _var("surface", theme)) >= 3, theme
        for seal in ("gold", "silver", "bronze"):
            assert _ratio(_var(seal, theme), _var("panel", theme)) >= 3, (theme, seal)


def test_the_three_seals_are_words_with_distinct_borders():
    assert ".seal-steady { color: var(--silver); border-style: double" in CSS and ".seal-rough { color: var(--bronze); border-style: dashed; }" in CSS
    assert 'el("span", "seal seal-" + name.toLowerCase(), name)' in APP


def test_a_restless_room_has_a_thick_border_and_the_word_and_a_still_room_a_dotted_one():
    assert ".room.restless { border-color: var(--accent); border-width: 4px; }" in CSS and ".room.still { border-style: dotted;" in CSS
    assert ".room.unknown { border-style: dashed; }" in CSS
    for needle in ("\u25C6 Restless", "\u25C7 Still", "Not entered yet"):
        assert needle in APP


def test_the_room_you_are_in_is_told_in_words_as_well_as_an_outline():
    assert '" · you are here"' in APP and ".room.here { box-shadow: inset 0 0 0 3px var(--focus); }" in CSS


def test_a_packed_piece_of_equipment_has_a_thick_border_and_the_words_in_the_bag():
    assert '.gear[aria-pressed="true"] { border-color: var(--accent); border-width: 4px;' in CSS and '"In the bag"' in APP and "aria-pressed" in APP
    assert ".gear .letter" in CSS and 'el("span", "letter", g.letter)' in APP


def test_readings_differ_by_border_style_and_words():
    for needle in (".nb td.r-2 { border: 2px solid", ".nb td.r-1 { border-style: dotted;", ".nb td.r-3 { border-style: dashed;"):
        assert needle in CSS
    assert 'c.state === 3 ? "Doubt" : c.word' in APP and "aria-label" in APP
    for word in ("Yes", "No", "Doubtful", "not read"):
        assert '"%s"' % word in (GAME_DIR / "game.py").read_text(encoding="utf-8")


def test_ruled_out_suspects_are_struck_through_as_well_as_dimmed_and_the_setting_can_turn_it_off():
    assert "text-decoration: line-through" in CSS and 'html[data-narrow="off"] .sheet li.ruled-out' in CSS and 'html[data-narrow="off"] .suspect.ruled-out' in CSS
    assert 'id="narrow-checkbox"' in HTML and "ruled out by your notebook" in APP


def test_a_picked_suspect_differs_by_border_width_not_only_colour():
    assert '.suspect[aria-pressed="true"] { border-color: var(--accent); border-width: 4px;' in CSS and ', picked' in APP


def test_the_page_has_the_blanket_hidden_rule_and_reduced_motion_support():
    assert "[hidden] { display: none !important; }" in CSS
    assert 'html[data-reduced-motion="true"]' in CSS and 'html[data-effects="off"]' in CSS


def test_live_regions_labels_skip_link_and_landmarks():
    assert 'class="sr-only"' in HTML and 'aria-live="polite"' in HTML and "aria-label" in APP
    assert 'class="skip-link" href="#case-panel"' in HTML and 'id="case-panel"' in HTML and "<main" in HTML
    assert 'role="group" aria-label="Floor plan"' in HTML and 'role="group" aria-label="Equipment"' in HTML


def test_emblems_and_the_scene_have_text_names_for_screen_readers():
    for kind in lx.KIND_IDS:
        svg = render.emblem(kind)
        assert 'role="img" aria-label="%s emblem"' % lx.KIND_NAME[kind] in svg and svg.count("<polygon") >= 3
    assert 'aria-label="A house at night"' in render.scene(3)


def test_every_kind_has_its_own_emblem_shape_or_colour():
    seen = {lx.KIND_EMBLEM[k] for k in lx.KIND_IDS}
    assert len(seen) == 12


def test_touch_targets_are_covered_by_the_shared_sheet():
    assert "shared/touch-targets.css" in HTML


def test_the_notebook_table_has_headers_and_the_page_does_not_scroll_sideways():
    assert 'setAttribute("scope", "col")' in APP and "overflow-x: auto" in CSS
    assert "min-width: 0" in CSS


def test_destructive_actions_ask_first():
    assert 'askThen("evidence-hunt-reset"' in APP and 'askThen("evidence-hunt-restore"' in APP and 'askThen("evidence-hunt-accuse"' in APP


def test_the_tutorial_only_points_at_things_the_page_has():
    ids = set(re.findall(r'(?<![-\w])id="([^"]+)"', HTML))
    steps = APP.split("var TUTORIAL_STEPS = [")[1].split("];")[0]
    selectors = re.findall(r'selector: "#([\w-]+)"', steps)
    assert len(selectors) >= 8 and set(selectors) <= ids
    assert 'id="tutorial-restart-button"' in HTML and "evidenceHuntTutorialSteps" in HTML and "tutorial.js" in HTML
    assert "GameTutorial.init" in APP and 'gameId: "evidence-hunt"' in APP
    assert steps.count("title:") == steps.count("text:") >= 10


def test_the_about_page_states_the_fiction_notice_and_the_pledge():
    import info
    assert "fiction game" in info.NOTICE and "invented" in info.NOTICE
    assert 'id="info-page-notice"' in HTML and "fiction game" in HTML.lower()
    assert len(info.PLEDGE) >= 6 and any("No audio" in p for p in info.PLEDGE) and any("wrong spirit" in p.lower() or "wrong" in p.lower() for p in info.PLEDGE)
    assert len(info.HOW) >= 5


def test_the_keyboard_help_lists_the_shortcuts_the_page_really_has():
    assert "1 to 6: pack or unpack" in HTML and "n >= 1 && n <= 6" in APP
    for toggle in ("cases-toggle-button", "practice-toggle-button", "guide-toggle-button", "changelog-toggle-button", "settings-toggle-button", "info-page-toggle-button"):
        assert '{ toggle: "%s"' % toggle in HTML


def test_the_light_theme_restyles_the_bare_lists_and_sets_every_variable():
    dark = set(re.findall(r"--([a-z-]+):", CSS.split(":root {")[1].split("}")[0]))
    light = set(re.findall(r"--([a-z-]+):", CSS.split('html[data-theme="light"] {')[1].split("}")[0]))
    assert dark == light, dark ^ light
    assert 'html[data-theme="light"] ul.chips' in CSS and 'html[data-theme="light"] ul.guide-list' in CSS


def test_display_settings_are_per_device_and_not_in_the_save():
    js = (GAME_DIR / "settings.js").read_text(encoding="utf-8")
    assert "evidence-hunt-text-scale" in js and "NOT part of get_state" in js and "prefers-reduced-motion" in js
    import json

    import game
    game.game.__init__()
    assert not re.search(r"scale|motion|contrast|theme|narrow", json.dumps(game.get_state()), flags=re.I)
