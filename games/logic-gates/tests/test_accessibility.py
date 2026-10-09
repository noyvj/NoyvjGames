"""Milestone 5: accessibility, light theme, display settings and the standard kit. The page is plain files, so these are source-level
checks: contrast is computed from the real colour variables, every state is checked for a non-colour cue, and the markup is checked for
the labels and live regions the script depends on."""

import json
import re
from html.parser import HTMLParser
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")
CSS = (GAME_DIR / "style.css").read_text(encoding="utf-8")
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")
SETTINGS = (GAME_DIR / "settings.js").read_text(encoding="utf-8")
RENDER = (GAME_DIR / "render.py").read_text(encoding="utf-8")


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
TEXT_PAIRS = [("--text", "--bg"), ("--text", "--panel"), ("--text", "--surface"), ("--text", "--btn"), ("--text", "--chip"), ("--muted", "--panel"),
              ("--muted", "--bg"), ("--muted", "--surface"), ("--accent", "--panel"), ("--accent", "--bg"), ("--on-primary", "--btn-primary"),
              ("--good", "--panel"), ("--bad", "--panel"), ("--good", "--surface"), ("--halo", "--lamp"), ("--muted", "--chip")]
UI_PAIRS = [("--edge", "--panel"), ("--edge", "--surface"), ("--focus", "--panel"), ("--focus", "--bg"), ("--hover-edge", "--panel"),
            ("--wire-on", "--surface"), ("--wire-off", "--surface"), ("--lamp", "--surface"), ("--chip-edge", "--chip"), ("--pin", "--pin-fill"),
            ("--float", "--surface"), ("--chip-edge", "--surface")]


def test_both_themes_define_every_colour_variable():
    assert set(DARK) == set(_variables('html[data-theme="light"]')), "the light theme must override every variable"


def test_text_contrast_is_at_least_aa_in_both_themes():
    for name, theme in (("night blueprint", DARK), ("drafting sheet", LIGHT)):
        for fg, bg in TEXT_PAIRS:
            assert contrast(theme[fg], theme[bg]) >= 4.5, f"{name}: {fg} on {bg} is {contrast(theme[fg], theme[bg]):.2f}"


def test_lines_pins_wires_and_focus_rings_are_at_least_three_to_one_in_both_themes():
    for name, theme in (("night blueprint", DARK), ("drafting sheet", LIGHT)):
        for fg, bg in UI_PAIRS:
            assert contrast(theme[fg], theme[bg]) >= 3.0, f"{name}: {fg} on {bg} is {contrast(theme[fg], theme[bg]):.2f}"


def test_the_stylesheet_uses_variables_not_loose_colours_below_the_themes():
    body = CSS.split("* { box-sizing")[1]
    assert not re.search(r"#[0-9a-fA-F]{6}\b", body), "use the colour variables so both themes and high contrast apply"


def test_a_wire_value_is_shape_not_colour_and_a_lamp_says_its_digit():
    one = re.search(r"^\.lg-w1\s*\{([^}]*)\}", CSS, re.M).group(1)
    zero = re.search(r"^\.lg-w0\s*\{([^}]*)\}", CSS, re.M).group(1)
    assert "stroke-dasharray" in zero and "stroke-dasharray" not in one
    assert float(re.search(r"stroke-width:\s*([\d.]+)", one).group(1)) > float(re.search(r"stroke-width:\s*([\d.]+)", zero).group(1))
    assert 'class="lg-val"' in RENDER                                   # the digit is drawn on every switch and lamp
    assert ".lg-lamp.lg-on rect" in CSS and "stroke-dasharray: none" in CSS.split(".lg-lamp.lg-on rect")[1].split("}")[0]
    assert ".lg-pin.lg-floating" in CSS and "stroke-dasharray" in CSS.split(".lg-pin.lg-floating")[1].split("}")[0]


def test_state_cues_are_words_not_colour_alone():
    assert 'content: "Wrong"' in CSS and 'content: "Right"' in CSS
    assert 'content: "Found: "' in CSS and 'content: "Not yet: "' in CSS
    assert '.picker-list button[aria-current="true"]' in CSS and "border-width: 3px" in CSS.split('.picker-list button[aria-current="true"]')[1].split("}")[0]
    assert 'button[aria-disabled="true"]' in CSS and "dashed" in CSS.split('button[aria-disabled="true"]')[1].split("}")[0]
    assert ".switches button[aria-pressed=\"true\"]" in CSS and 'name + " = "' in APP        # a switch says its value in words


def test_the_light_theme_follows_the_site_theme_and_has_its_own_control():
    assert 'html[data-theme="light"]' in CSS and "theme-setting-button" in HTML and "NoyvjTheme" in SETTINGS
    assert "noyvj-theme-change" in SETTINGS


def test_reduced_motion_effects_and_high_contrast_are_wired_to_the_page():
    for attr in ("data-reduced-motion", "data-effects", "data-high-contrast"):
        assert attr in SETTINGS and attr in CSS, attr
    assert "prefers-reduced-motion" in SETTINGS and "prefers-reduced-motion" in CSS


def test_text_size_has_bounds_and_the_page_scales_with_it():
    assert "MIN_SCALE = 0.85" in SETTINGS and "MAX_SCALE = 1.5" in SETTINGS and "calc(100% * var(--text-scale, 1))" in CSS


class _Collect(HTMLParser):
    def __init__(self):
        super().__init__()
        self.inputs, self.labels_for, self.live, self.ids, self.html_lang = [], set(), [], [], None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.html_lang = a.get("lang")
        if "id" in a:
            self.ids.append(a["id"])
        if tag == "input":
            self.inputs.append(a)
        if tag == "label" and "for" in a:
            self.labels_for.add(a["for"])
        if "aria-live" in a or a.get("role") in ("status", "alert"):
            self.live.append(a.get("id"))


PARSED = _Collect()
PARSED.feed(HTML)


def test_the_page_has_a_language_a_skip_link_and_unique_ids():
    assert PARSED.html_lang == "en" and 'class="skip-link"' in HTML
    assert len(PARSED.ids) == len(set(PARSED.ids))


def test_text_size_buttons_have_names_and_every_checkbox_is_labelled():
    for needle in ('aria-label="Decrease text size"', 'aria-label="Increase text size"', 'aria-label="Reset text size"'):
        assert needle in HTML
    for i in PARSED.inputs:
        assert i.get("id") in PARSED.labels_for or "aria-label" in i or i.get("id") in ("reduced-motion-checkbox", "effects-checkbox", "high-contrast-checkbox"), i
    for id_ in ("reduced-motion-checkbox", "effects-checkbox", "high-contrast-checkbox"):
        assert re.search(rf"<label><input[^>]*id=\"{id_}\"", HTML)


def test_every_control_the_script_builds_has_a_label():
    assert 'lab.setAttribute("for", id)' in APP and "sel.id = id" in APP          # every connection list is labelled
    assert "aria-label" in APP and "Remove chip" in APP and "Switch \" + name" in APP


def test_status_text_is_in_live_regions():
    for needle in ('id="toast"', 'id="announce"', 'id="level-goal"', 'id="result-summary"', 'id="wiring-status"', 'id="board-count"', 'id="hint-rung"'):
        assert needle in HTML
    assert PARSED.live and "announce(" in APP


def test_the_drawing_is_an_image_with_a_text_twin_and_the_same_job_is_doable_from_lists():
    assert 'role="img"' in RENDER and "<title" in RENDER
    assert 'id="words"' in HTML and "The circuit in words" in HTML
    assert 'selectFor("pin-" + p.dest' in APP and 'selectFor("pin-" + l.dest' in APP          # every wire can be made without the pointer
    assert "tabindex=\"0\"" in HTML and "scrolls sideways" in HTML                           # the wide drawing can be scrolled by keyboard


def test_a_disabled_control_stays_focusable_so_focus_is_not_thrown_to_the_top():
    assert 'setAttribute("aria-disabled"' in APP and "function guard(" in APP


def test_every_standard_shared_piece_is_present():
    for piece in ("tutorial.js", "confirm-dialog.js", "save-widget.js", "opening-screen.js", "story-toggle.js", "keyboard-shortcuts.js", "last-played.js",
                  "whats-new-banner.js", "achievement-share.js", "a11y.css", "touch-targets.css", "theme.js", "lite-mode.js", "report-problem.js", "profile.js"):
        assert piece in HTML, piece
    assert "ConfirmDialog.ask" in APP and "GameTutorial.init" in APP


def test_the_changelog_is_valid_and_dated():
    data = json.loads((GAME_DIR / "changelog.json").read_text(encoding="utf-8"))
    entries = data["changelog"]
    assert entries and all(re.match(r"\d{4}-\d{2}-\d{2}$", e["date"]) and e["entry"].strip() for e in entries)
    assert "window.CHANGELOG_JSON" in APP


def test_the_about_page_names_a_source_and_a_read_date_for_every_fact_and_says_it_is_a_game():
    import info
    v = info.view()
    assert "not a hardware simulator" in v["framing"] and len(v["facts"]) >= 5
    for fact in v["facts"]:
        s = fact["source"]
        assert s["url"].startswith("https://") and s["title"] and s["publisher"] and s["date_read"] == "2026-10-09"
        assert fact["fact"].strip() and fact["tie_in"].strip()
    assert "info-page-source-note" in APP and "Read on" in APP


def test_the_story_toggle_hides_only_story_elements():
    m = re.search(r'data-story-selectors="([^"]+)"', HTML).group(1)
    assert {s.strip() for s in m.split(",")} == {"#level-intro", "#level-log", "#log-panel", "#log-toggle-button"}


def test_the_tutorial_points_only_at_things_that_exist():
    steps = re.findall(r'selector: "(#[\w-]+)"', APP)
    assert len(steps) >= 6
    for selector in steps:
        assert f'id="{selector[1:]}"' in HTML, selector
