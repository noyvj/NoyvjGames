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
        assert _ratio(_var("muted", theme), _var("ines", theme)) >= 4.5, theme
        assert _ratio(_var("accent", theme), _var("panel", theme)) >= 4.5, theme
        assert _ratio(_var("accent", theme), _var("surface", theme)) >= 4.5, theme
        assert _ratio(_var("focus", theme), _var("panel", theme)) >= 3, theme
        assert _ratio(_var("on-primary", theme), _var("btn-primary", theme)) >= 4.5, theme
        assert _ratio(_var("text", theme), _var("btn", theme)) >= 4.5, theme
        assert _ratio(_var("text", theme), _var("surface", theme)) >= 4.5, theme
        assert _ratio(_var("text", theme), _var("you", theme)) >= 7, theme
        assert _ratio(_var("text", theme), _var("ines", theme)) >= 7, theme
        assert _ratio(_var("ok", theme), _var("panel", theme)) >= 3, theme
        assert _ratio(_var("bad", theme), _var("panel", theme)) >= 3, theme
        assert _ratio(_var("cool", theme), _var("surface", theme)) >= 3, theme
        assert _ratio(_var("you-edge", theme), _var("surface", theme)) >= 3, theme


def test_your_messages_and_hers_differ_by_side_border_weight_and_a_name_not_only_colour():
    assert ".msg.ines { align-self: flex-start;" in CSS and ".msg.you { align-self: flex-end;" in CSS and "border: 2px solid var(--you-edge)" in CSS
    assert '"Ines"' in APP and '"You"' in APP


def test_the_stats_are_a_number_and_a_word_as_well_as_a_bar():
    for name in ("trust", "supplies", "hope"):
        assert f'id="stat-{name}-value"' in HTML and f'id="stat-{name}-word"' in HTML and f'id="stat-{name}-fill"' in HTML
    assert 'aria-hidden="true"><span id="stat-trust-fill"' in HTML


def test_a_tried_reply_says_tried_and_a_shut_reply_is_dashed_with_its_reason_written_out():
    assert '"Tried"' in APP and ".choice.locked { border-style: dashed;" in CSS
    assert 'el("span", "why", c.why)' in APP and "Shut for now: " in APP and 'setAttribute("aria-disabled", "true")' in APP


def test_the_page_has_the_blanket_hidden_rule_and_reduced_motion_support():
    assert "[hidden] { display: none !important; }" in CSS
    assert 'html[data-reduced-motion="true"]' in CSS and 'html[data-effects="off"]' in CSS


def test_live_regions_labels_skip_link_and_landmarks():
    assert 'class="sr-only"' in HTML and 'aria-live="polite"' in HTML and "aria-label" in APP
    assert 'class="skip-link" href="#comms-panel"' in HTML and 'id="comms-panel"' in HTML and "<main" in HTML
    assert 'role="log"' in HTML and 'role="group" aria-label="Your reply"' in HTML


def test_portraits_and_the_scene_have_a_text_name_for_screen_readers():
    assert 'role="img" aria-label="Ines Varga"' in render.ines()
    assert 'role="img" aria-label="Bit, the small robot"' in render.bit()
    assert 'aria-label="Sparrow Relay on Orrin, day 3"' in render.scene(3)
    assert 'aria-hidden="true"' in render.map_svg([])


def test_messages_can_arrive_one_at_a_time_by_tap_and_nothing_uses_a_timer_for_it():
    assert 'id="reveal-select"' in HTML and "data-reveal" in APP and "Next message" in APP
    settings = (GAME_DIR / "settings.js").read_text(encoding="utf-8")
    assert "setTimeout" not in settings and "setInterval" not in settings and "setInterval" not in APP


def test_touch_targets_are_covered_by_the_shared_sheet():
    assert "shared/touch-targets.css" in HTML


def test_destructive_actions_ask_first_and_rewinding_does_not_need_to():
    assert 'askThen("stranded-reset"' in APP
    assert "askThen" not in APP.split("Rewind to here")[1].split("return node")[0]


def test_the_tutorial_only_points_at_things_the_page_has():
    ids = set(re.findall(r'(?<![-\w])id="([^"]+)"', HTML))
    steps = APP.split("var TUTORIAL_STEPS = [")[1].split("];")[0]
    selectors = re.findall(r'selector: "#([\w-]+)"', steps)
    assert len(selectors) >= 5 and set(selectors) <= ids
    assert 'id="tutorial-restart-button"' in HTML and "strandedTutorialSteps" in HTML and "tutorial.js" in HTML


def test_the_about_page_the_whats_new_panel_and_the_shortcut_help_exist():
    for needle in ('id="info-page-panel"', 'id="info-page-notice"', 'id="facts-list"', 'id="changelog-panel"', 'id="changelog-entries"', "KeyboardShortcuts.init", "1 to 4: send that reply"):
        assert needle in HTML
    assert "Read on " in APP and 'link.rel = "noopener noreferrer"' in APP


def test_every_panel_toggle_is_in_the_keyboard_shortcut_config_so_escape_closes_it():
    for toggle in re.findall(r'id="([\w-]+-toggle-button)"', HTML):
        assert f'toggle: "{toggle}"' in HTML, toggle


def test_one_message_per_tap_is_the_default_and_the_narrator_line_is_off_by_default():
    settings = (GAME_DIR / "settings.js").read_text(encoding="utf-8")
    assert 'get(REVEAL_KEY) === "instant" ? "instant" : "tap"' in settings          # AN-7
    assert 'get(NARRATOR_KEY) === "true"' in settings and 'id="narrator-checkbox"' in HTML      # AN-10: off until switched on
    assert "narratorShown" in APP and "listOf(view.transcript)" in APP               # a hidden line never costs a tap


def test_harbours_quick_reassurance_flaw_is_in_the_story_and_the_tenth_ending_is_reachable():
    import story
    flagged = [sid for sid, s in story.SCENES.items() if any("quick" in c["set"] for c in s["choices"])]
    assert flagged == ["d2a", "d4b", "d6a"]
    assert any(c["need"] and "quick" in c["need"]["all"] and "owned" in c["set"] for c in story.SCENES["d7a"]["choices"])
    assert "asleep" in story.ENDING_IDS and len(story.ENDING_IDS) == 10
