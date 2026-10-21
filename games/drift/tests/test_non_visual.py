"""I-5: the non-visual view (tables + one-sentence summary), shown by the Non-Visual Mode button."""
import json
import re

from tests.pagefiles import GAME_DIR, game_css, page_text


def _render_after_two_rounds(game_env):
    game_env.region.invest("housing")
    game_env.advance_round()
    game_env.advance_round()
    game_env.module.render()
    return game_env.elements


def test_status_table_lists_each_capacity_type_in_words(game_env):
    # After one housing purchase the status table must state housing 10 and the other two types 0.
    game_env.region.invest("housing")
    game_env.module.render()
    html = game_env.elements["nv-status-body"].innerHTML
    assert '<th scope="row">Housing capacity</th><td>10</td>' in html
    assert '<th scope="row">Integration Services capacity</th><td>0</td>' in html
    assert '<th scope="row">Infrastructure capacity</th><td>0</td>' in html
    assert '<th scope="row">Round</th><td>1</td>' in html


def test_arrival_table_numbers_past_rounds_newest_first(game_env):
    # Two advances leave rounds 1 and 2 in the log; the table shows the current round 3, then 2, then 1.
    elements = _render_after_two_rounds(game_env)
    rows = re.findall(r"<th scope=\"row\">([^<]*)</th>", elements["nv-arrival-body"].innerHTML)
    assert rows == ["Round 3 (now)", "Round 2", "Round 1"]


def test_arrival_table_gives_dots_as_words(game_env):
    game_env.module.render()
    assert " dots</td>" in game_env.elements["nv-arrival-body"].innerHTML


def test_gauge_trend_is_a_word_not_only_an_arrow(game_env):
    # Before two rounds exist the trend says so in words; afterwards it is one of the trend words.
    game_env.module.render()
    assert "not enough rounds yet" in game_env.elements["nv-gauges-body"].innerHTML
    elements = _render_after_two_rounds(game_env)
    gauges = elements["nv-gauges-body"].innerHTML
    assert "not enough rounds yet" not in gauges
    assert re.search(r"<td>(improving|plateauing|declining)</td>", gauges)


def test_summary_sentence_names_round_funds_strain_and_wellbeing(game_env):
    game_env.region.invest("housing")
    game_env.module.render()
    text = game_env.elements["non-visual-summary"].innerText
    assert text.startswith("Round 1. Funds 280. Strain ")
    assert text.endswith(" of 100.")
    assert "Wellbeing" in text


def test_tables_are_visible_only_when_the_mode_class_is_on():
    css = game_css()
    assert re.search(r"\.non-visual-section\s*\{\s*display:\s*none", css)
    assert re.search(r"html\.non-visual-mode \.non-visual-section\s*\{\s*display:\s*block", css)


def test_button_toggles_the_class_the_css_uses_and_reset_clears_it():
    js = (GAME_DIR / "settings.js").read_text(encoding="utf-8")
    assert js.count('applyFlag(nonVisualKey, "non-visual-mode"') == 3  # on load, on click, in Reset
    assert 'applyFlag(nonVisualKey, "non-visual-mode", false)' in js
    html = page_text()
    assert 'id="non-visual-toggle-button"' in html
    assert 'id="non-visual-summary" role="status" aria-live="polite"' in html


def test_every_id_the_renderer_fills_is_in_the_page():
    html = page_text()
    for element_id in ("nv-status-body", "nv-arrival-body", "nv-gauges-body", "non-visual-summary"):
        assert f'id="{element_id}"' in html


def test_desktop_page_has_the_button_in_the_game_menu_and_the_tables_in_the_stage():
    config = json.loads((GAME_DIR / "pc-config.json").read_text(encoding="utf-8"))
    game_menu = next(g for g in config["toolbar"]["menu"] if g["heading"] == "Game")
    assert "non-visual-toggle-button" in game_menu["ids"]
    assert "#non-visual-tables" in config["zones"]["stage"]
