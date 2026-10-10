"""Herd Round-5 display preferences: F-15 high contrast and easy-read font toggles, F-14 pattern
fills and shape markers. The toggles themselves are plain JS (settings.js) so these tests check the
wiring in the files plus the Python-drawn markers and bars."""

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
SETTINGS_JS = (HERE / "settings.js").read_text(encoding="utf-8")
STYLE_CSS = (HERE / "style.css").read_text(encoding="utf-8")
INDEX_HTML = (HERE / "index.html").read_text(encoding="utf-8")
PC_HTML = (HERE / "pc.html").read_text(encoding="utf-8")

PREFS = [
    ("herd-high-contrast", "data-high-contrast", "high-contrast-checkbox"),
    ("herd-dyslexia-font", "data-dyslexia-font", "dyslexia-font-checkbox"),
    ("herd-hatch-patterns", "data-hatch-patterns", "hatch-patterns-checkbox"),
]


def test_every_preference_is_wired_in_settings_js_and_both_pages():
    for key, attr, checkbox in PREFS:
        assert f'"{key}"' in SETTINGS_JS and f'"{attr}"' in SETTINGS_JS
        assert f'id="{checkbox}"' in INDEX_HTML
        assert f'id="{checkbox}"' in PC_HTML


def test_every_preference_has_css_and_resets_with_the_default_button():
    for _key, attr, _checkbox in PREFS:
        assert f'html[{attr}="true"]' in STYLE_CSS
    assert "resetDisplayPrefs();" in SETTINGS_JS


def test_preferences_are_browser_level_not_saved_in_the_game_state(game_env):
    state = game_env.module.get_state()
    assert not any("contrast" in k or "dyslexia" in k or "hatch" in k for k in state)


def test_trend_graph_draws_a_marker_per_round_with_shapes_for_meaning(game_env):
    m = game_env.module
    svg = m.methane_trend_graph_svg([0.0, 5.0, 12.0, 17.0, 20.0, 20.0])
    assert svg.count("trend-marker") == 6 + svg.count("trend-marker--")  # class + modifier on each
    assert "<polygon" in svg and svg.count("<polygon") == 1  # only the latest round is a diamond
    assert "trend-marker--flat" in svg and "trend-marker--rise" in svg
    assert "<circle" in svg and "<rect" in svg


def test_a_flat_round_is_a_square_and_a_rising_round_a_circle(game_env):
    m = game_env.module
    # increments: +10, +10 (not flatter), +5 (flatter)
    svg = m.methane_trend_graph_svg([0.0, 10.0, 20.0, 25.0, 25.0])
    assert svg.count("trend-marker--flat") == 1
    assert svg.count("trend-marker--rise") == 3


def test_markers_are_capped_for_a_long_game(game_env):
    m = game_env.module
    svg = m.methane_trend_graph_svg([float(i * i) for i in range(120)])
    assert len(re.findall(r'class="trend-marker', svg)) == 40


def test_markers_are_hidden_until_the_pattern_setting_is_on():
    assert re.search(r"\.trend-marker \{ display: none;", STYLE_CSS)
    assert 'html[data-hatch-patterns="true"] .trend-marker { display: inline; }' in STYLE_CSS


def test_welfare_and_supply_chain_bars_follow_the_state(game_env):
    m = game_env.module
    el = game_env.elements
    assert el["welfare-bar"].style.width == "50%"
    assert el["supply-chain-bar"].style.width == "0%"
    game_env.farm.funds = 1000.0
    game_env.invest_decoupling("feed")
    game_env.invest_decoupling("feed")
    assert el["welfare-bar"].style.width == f"{(m.WELFARE_START + 2 * m.WELFARE_FEED):.0f}%"
    game_env.elements["supply-chain-invest-button"].dispatch("click", None)
    assert el["supply-chain-bar"].style.width == f"{100 / m.SUPPLY_CHAIN_MAX_UNITS:.0f}%"
