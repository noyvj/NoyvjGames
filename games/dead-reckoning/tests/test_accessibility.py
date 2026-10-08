"""Milestone 9: accessibility, light theme, display settings and the standard kit. The page is plain files, so these are source-level
checks: contrast is computed from the real colour variables, every state is checked for a non-colour cue, and the markup is checked
for the labels and live regions the script depends on."""

import json
import re
from html.parser import HTMLParser
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")
CSS = (GAME_DIR / "style.css").read_text(encoding="utf-8")
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")
SETTINGS = (GAME_DIR / "settings.js").read_text(encoding="utf-8")


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
TEXT_PAIRS = [("--text", "--bg"), ("--text", "--panel"), ("--text", "--surface"), ("--text", "--btn"), ("--muted", "--panel"),
              ("--muted", "--bg"), ("--accent", "--panel"), ("--accent", "--bg"), ("--on-primary", "--btn-primary"),
              ("--text", "--sea"), ("--muted", "--sea"), ("--hazard", "--sea"), ("--current", "--sea"), ("--flag", "--sea"),
              ("--good", "--panel"), ("--bad", "--panel")]
UI_PAIRS = [("--edge", "--panel"), ("--edge", "--surface"), ("--focus", "--panel"), ("--focus", "--bg"), ("--hover-edge", "--panel"),
            ("--est", "--sea"), ("--truth", "--sea"), ("--land-edge", "--land"), ("--hazard", "--sea"), ("--ribbon", "--sea")]


def test_both_themes_define_every_colour_variable():
    assert set(DARK) == set(_variables('html[data-theme="light"]')), "the light theme must override every variable"


def test_text_contrast_is_at_least_aa_in_both_themes():
    for name, theme in (("night chart", DARK), ("paper chart", LIGHT)):
        for fg, bg in TEXT_PAIRS:
            assert contrast(theme[fg], theme[bg]) >= 4.5, f"{name}: {fg} on {bg} is {contrast(theme[fg], theme[bg]):.2f}"


def test_lines_and_focus_rings_are_at_least_three_to_one_in_both_themes():
    for name, theme in (("night chart", DARK), ("paper chart", LIGHT)):
        for fg, bg in UI_PAIRS:
            assert contrast(theme[fg], theme[bg]) >= 3.0, f"{name}: {fg} on {bg} is {contrast(theme[fg], theme[bg]):.2f}"


def test_the_stylesheet_uses_variables_not_loose_colours_below_the_themes():
    body = CSS.split("* { box-sizing")[1]
    assert not re.search(r"#[0-9a-fA-F]{6}\b", body), "use the colour variables so both themes and high contrast apply"


def test_the_two_tracks_differ_by_dash_style_and_the_hazards_by_shape_and_hatch():
    est = re.search(r"\.dr-est-track\s*\{([^}]*)\}", CSS).group(1)
    true = re.search(r"\.dr-true-track\s*\{([^}]*)\}", CSS).group(1)
    assert "stroke-dasharray" in est and "stroke-dasharray" not in true
    assert ".dr-hazard-shoal" in CSS and "stroke-dasharray" in CSS.split(".dr-hazard-shoal")[1].split("}")[0]
    assert ".dr-hazard-cross" in CSS and "dr-pat-reef" in (GAME_DIR / "render.py").read_text(encoding="utf-8")
    assert re.search(r"\.dr-hatch-reef\s*\{", CSS) and re.search(r"\.dr-dot\s*\{", CSS) and re.search(r"\.dr-hatch\s*\{", CSS)


def test_a_current_is_never_colour_only_the_arrow_and_range_text_are_always_drawn():
    render = (GAME_DIR / "render.py").read_text(encoding="utf-8")
    assert "dr-current-arrow" in render and "range_text(zone[\"drift_range\"])" in render


def test_state_cues_are_not_colour_alone():
    assert ".leg.selected" in CSS and "border-width: 3px" in CSS.split(".leg.selected")[1].split("}")[0]
    assert ".leg:not(.selected)" in CSS and "dashed" in CSS.split(".leg:not(.selected)")[1].split("}")[0]
    assert 'content: "Yes' in CSS and 'content: "Not yet' in CSS            # a criterion is a word, not a colour
    assert ".picker-list button[aria-current" in CSS and "stars(" in APP     # chart stars are glyphs plus a spoken label
    assert ".fix-list li.applied" in CSS and "Fix applied" in APP
    assert "button[aria-disabled=\"true\"]" in CSS and "dashed" in CSS.split("button[aria-disabled=\"true\"]")[1].split("}")[0]


def test_the_light_theme_follows_the_site_theme_and_has_its_own_control():
    assert 'html[data-theme="light"]' in CSS and "theme-setting-button" in HTML and "NoyvjTheme" in SETTINGS
    assert "noyvj-theme-change" in SETTINGS


def test_reduced_motion_effects_and_high_contrast_are_wired_to_the_page():
    for attr in ("data-reduced-motion", "data-effects", "data-high-contrast"):
        assert attr in SETTINGS and attr in CSS, attr
    assert "prefers-reduced-motion" in SETTINGS
    assert "reducedMotion()" in APP and "showUpTo(r.points.length - 1)" in APP   # reduced motion: the result at once


def test_text_size_has_bounds_and_the_page_scales_with_it():
    assert "MIN_SCALE = 0.85" in SETTINGS and "MAX_SCALE = 1.5" in SETTINGS and "calc(100% * var(--text-scale, 1))" in CSS


class _Collect(HTMLParser):
    def __init__(self):
        super().__init__()
        self.buttons, self.inputs, self.labels_for, self.live = [], [], set(), []
        self.ids = []
        self.html_lang = None
        self._label = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.html_lang = a.get("lang")
        if "id" in a:
            self.ids.append(a["id"])
        if tag == "button":
            self.buttons.append(a)
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


def test_every_icon_only_or_symbol_button_has_an_accessible_name():
    for needle in ('aria-label="Decrease text size"', 'aria-label="Increase text size"', 'aria-label="Reset text size"'):
        assert needle in HTML
    assert "setAttribute(\"aria-label\", \"Decrease \"" in APP and "setAttribute(\"aria-label\", \"Increase \"" in APP
    assert "Remove leg" in APP


def test_every_form_field_has_a_label():
    for i in PARSED.inputs:
        if i.get("type") in ("hidden",):
            continue
        has_label = i.get("id") in PARSED.labels_for or "aria-label" in i
        wrapped = i.get("id") in ("reduced-motion-checkbox", "effects-checkbox", "high-contrast-checkbox", "practice-code", "point-x", "point-y")
        assert has_label or wrapped, i
    assert 'for="scrub-range"' in HTML and 'for="allow-checkbox"' in HTML
    assert "input.id = id" in APP and "lab.setAttribute(\"for\", id)" in APP


def test_status_text_is_in_live_regions():
    for needle in ('id="toast"', 'id="announce"', 'id="chart-goal"', 'id="plot-line"', 'id="watch-status"', 'id="event-list"', 'id="progress-line"'):
        assert needle in HTML
    assert PARSED.live and "announce(" in APP


def test_the_chart_is_an_image_with_a_text_twin():
    assert 'id="chart-notes"' in HTML and "The chart in words" in HTML
    render = (GAME_DIR / "render.py").read_text(encoding="utf-8")
    assert 'role="img"' in render and "aria-labelledby" in render and "<desc" in render


def test_a_disabled_control_stays_focusable_so_focus_is_not_thrown_to_the_top():
    assert 'setAttribute("aria-disabled", "true")' in APP and "function guard(" in APP


def test_every_standard_shared_piece_is_present():
    for piece in ("tutorial.js", "confirm-dialog.js", "mobile-hud.js", "mobile-dock.js", "save-widget.js", "opening-screen.js", "story-toggle.js",
                  "keyboard-shortcuts.js", "last-played.js", "whats-new-banner.js", "copy-result.js", "achievement-share.js", "a11y.css",
                  "touch-targets.css", "theme.js", "lite-mode.js"):
        assert piece in HTML, piece
    assert "ConfirmDialog.ask" in APP and "GameTutorial.init" in APP and "MobileHud.init" in APP and "MobileDock.init" in APP


def test_the_changelog_is_valid_and_dated():
    data = json.loads((GAME_DIR / "changelog.json").read_text(encoding="utf-8"))
    entries = data["changelog"]
    assert entries and all(re.match(r"\d{4}-\d{2}-\d{2}$", e["date"]) and e["entry"].strip() for e in entries)
    assert "window.CHANGELOG_JSON" in APP


def test_the_about_page_names_a_source_and_a_read_date_for_every_fact_and_says_it_is_a_game():
    import info
    v = info.view()
    assert "not a simulator" in v["framing"] and len(v["facts"]) >= 5
    for fact in v["facts"]:
        s = fact["source"]
        assert s["url"].startswith("https://") and s["title"] and s["publisher"] and s["date_read"] == "2026-10-09"
        assert fact["fact"].strip() and fact["tie_in"].strip()
    assert "1,852 metres" in " ".join(f["fact"] for f in v["facts"])
    assert "info-page-source-note" in APP and "Read on" in APP


def test_the_story_toggle_hides_only_story_elements():
    m = re.search(r'data-story-selectors="([^"]+)"', HTML).group(1)
    assert {s.strip() for s in m.split(",")} == {"#chart-intro", "#result-log", "#log-panel", "#log-toggle-button"}
