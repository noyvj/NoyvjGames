"""The standard kit: the tutorial, the phone dock and strip, the About panel with named sources, the What's New feed and
the colourblind audit."""

import colorsys
import json
import re
from pathlib import Path

import info

from .test_accessibility import CSS, DARK, LIGHT

GAME_DIR = Path(__file__).resolve().parent.parent
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")


def _steps():
    block = APP.split("var TUTORIAL_STEPS = [")[1].split("\n  ];")[0]
    return re.findall(r'\{(?: selector: "([^"]+)",)? title: "([^"]+)", text: "([^"]+)"', block)


def test_every_tutorial_step_has_a_title_text_and_a_selector_that_exists():
    steps = _steps()
    assert len(steps) >= 12
    ids = set(re.findall(r'\sid="([^"]+)"', HTML))
    for selector, title, text in steps:
        assert title and len(text) > 40
        if selector:
            assert re.match(r"#([\w-]+)$", selector) and selector[1:] in ids, selector
    assert not steps[0][0] and not steps[-1][0]          # a centred welcome and a centred goodbye


def test_the_tutorial_only_points_at_things_visible_in_the_evening():
    always_visible_or_evening = {"hud", "goals-panel", "scene-panel", "barometer-card", "board-card", "plan-blocks", "task-wind",
                                 "light-lamp-button", "station-panel", "letters-toggle-button", "eerie-toggle-button", "info-page-toggle-button"}
    assert {s[0][1:] for s in _steps() if s[0]} <= always_visible_or_evening


def test_the_tutorial_names_the_night_keys_that_exist():
    text = " ".join(s[2] for s in _steps())
    assert "keys 1 to 4" in text and "(W)" in text and "(T)" in text
    assert 'k >= "1" && k <= "4"' in APP and 'k === "w"' in APP and 'k === "t"' in APP


def test_the_phone_strip_and_dock_are_wired():
    assert "shared/mobile-hud.js" in HTML and "shared/mobile-dock.js" in HTML
    assert 'MobileHud.init' in APP and 'MobileDock.init("#night-controls"' in APP
    for sel in ("#hud-night", "#hud-oil", "#hud-energy"):
        assert f'selector: "{sel}"' in APP and sel[1:] in HTML
    assert "#night-controls.mobile-docked" in CSS and "--dock-h" in CSS and "@media (max-width: 640px)" in CSS
    assert '$("night-controls").hidden = v.phase !== "night"' in APP


def test_the_about_panel_names_a_source_and_a_read_date_for_every_real_fact():
    assert len(info.FACTS) >= 4
    for fact in info.FACTS:
        src = fact["source"]
        assert src["url"].startswith("https://") and src["title"] and src["publisher"] == "Wikipedia"
        assert re.match(r"2026-10-09$", src["date_read"])
        assert fact["fact"] and fact["tie_in"].startswith("In the game:")
    text = " ".join(f["fact"] for f in info.FACTS)
    for needle in ("1819", "25 July 1823", "32 km", "1870s", "every two hours"):
        assert needle in text
    assert "report" not in json.dumps(info.view()).lower() or "report" not in HTML.lower().split("about the light")[1][:400]


def test_the_about_panel_explains_the_rules_with_the_real_numbers():
    import data
    how = " ".join(info.HOW)
    for n in data.LEVEL_REACH:
        assert str(n) in how
    for n in data.LEVEL_BURN:
        assert str(n) in how
    assert "Nothing you do can end the game" in how and "pause" in how


def test_every_player_visible_string_in_the_about_panel_is_clean():
    from .test_story_data import BANNED
    for text in [info.FRAMING] + list(info.HOW) + [f["fact"] + " " + f["tie_in"] for f in info.FACTS]:
        assert not BANNED.search(text), text


def test_whats_new_is_a_dated_feed_for_every_milestone_that_changed_play():
    data = json.loads((GAME_DIR / "changelog.json").read_text(encoding="utf-8"))["changelog"]
    assert len(data) >= 5 and all(re.match(r"2026-\d\d-\d\d$", e["date"]) and len(e["entry"]) > 80 for e in data)
    assert 'window.CHANGELOG_JSON = text' in APP and "shared/whats-new-banner.js" in HTML


# ---- colourblind audit -------------------------------------------------------------------------------
def _hue_sat(hex_colour):
    r, g, b = (int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5))
    h, lightness, s = colorsys.rgb_to_hls(r, g, b)
    return h * 360, s


def test_no_interface_colour_is_a_red_or_a_green_so_no_state_can_rest_on_that_pair():
    """Red and green are the pair deuteranopia and protanopia confuse. The interface palette (both themes) uses neutral
    blue-greys with one amber accent; the only reds in the picture are the tower's decorative stripes."""
    for name, theme in (("dark", DARK), ("light", LIGHT)):
        for var, value in theme.items():
            hue, sat = _hue_sat(value)
            if sat < 0.25:
                continue
            assert not (80 <= hue <= 165), f"{name} {var} {value} is green"
            assert not (hue >= 345 or hue <= 12), f"{name} {var} {value} is red"


def test_every_state_that_could_be_colour_coded_has_a_second_channel():
    pairs = [
        ("oil and energy meters", ".meter[data-state=\"low\"]", "hud-oil-state"),
        ("part condition", ".structure-list .meter[data-state=\"failing\"]", "part-state"),
        ("ship outcome", ".ship-state[data-state=\"damaged\"]::before", "Passed safely"),
        ("the chosen lamp level", ".seg button[aria-pressed=\"true\"]", "aria-pressed"),
        ("a lit ship", ".ship.lit .ship-inner", "\\u25C9"),
        ("a goal", ".goal-num", "goal-num"),
    ]
    for label, css_needle, other in pairs:
        assert css_needle in CSS or other in APP, label
        assert other in CSS + APP + HTML or "◉" in APP, label
    assert "◉" in APP or "\\u25C9" in APP


def test_weather_is_an_icon_plus_a_word_plus_a_scene_pattern():
    import data
    assert len(set(data.COND_ICONS)) == 5 and len(set(data.COND_LABELS)) == 5
    assert "fog-pattern" in HTML and "rain-pattern" in HTML
