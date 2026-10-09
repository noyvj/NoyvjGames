"""B-7 (Canopy-owned part): the screen-reader live region says which plot is selected, why C, K or R did nothing, and
repeats a repeated message; plus the pieces of the keyboard grid cursor that live in the page."""

import pathlib

from .gb_helpers import make_mature

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _said(env):
    return env.elements["sr-announcer"].innerText.replace("​", "")


def test_selecting_a_plot_says_which_one_and_what_keys_act_on_it(game_env):
    m = game_env.module
    make_mature(m, 5)
    game_env.select(5)
    text = _said(game_env)
    assert text.startswith("Selected F1: Preserved, value 100.0, soil 100%")
    assert "Press C to clear it or K to clear-cut it" in text


def test_a_bare_plot_points_at_replant(game_env):
    m = game_env.module
    m.plots[2].state = m.BARE
    game_env.select(2)
    assert "Press R to replant it" in _said(game_env)


def test_a_replanting_plot_has_nothing_to_press(game_env):
    m = game_env.module
    m.plots[2].state = m.REPLANTING
    game_env.select(2)
    assert "Press" not in _said(game_env)


def test_clicking_a_tile_announces_like_the_keyboard_does(game_env):
    game_env.select_tile_click(7)
    assert _said(game_env).startswith("Selected B2:")


def test_the_heart_tree_is_selected_without_a_clear_hint(game_env):
    m = game_env.module
    m.heart_tree_index = 14
    game_env.select(14)
    assert "Press C" not in _said(game_env)


def test_c_on_a_bare_plot_says_why_nothing_happened(game_env):
    m = game_env.module
    m.plots[3].state = m.BARE
    game_env.select(3)
    assert m.hotkey_clear_selected() is False
    assert "already bare" in _said(game_env) and "Press R" in _said(game_env)


def test_c_on_a_replanting_plot_says_to_wait(game_env):
    m = game_env.module
    m.plots[3].state = m.REPLANTING
    game_env.select(3)
    assert m.hotkey_clear_selected() is False
    assert "replanting" in _said(game_env) and "wait" in _said(game_env)


def test_c_on_the_heart_tree_says_it_is_never_felled(game_env):
    m = game_env.module
    m.heart_tree_index = 14
    game_env.select(14)
    assert m.hotkey_clear_selected() is False
    assert "never felled" in _said(game_env)


def test_k_gives_the_same_reasons(game_env):
    m = game_env.module
    m.plots[3].state = m.BARE
    game_env.select(3)
    assert m.hotkey_clear_cut_selected() is False
    assert "already bare" in _said(game_env)


def test_r_on_a_standing_plot_says_only_bare_plots_are_replanted(game_env):
    game_env.select(3)
    assert game_env.module.hotkey_replant_selected() is False
    assert "only a bare plot can be replanted" in _said(game_env)


def test_in_survey_mode_a_refused_key_points_at_the_plan(game_env):
    m = game_env.module
    m.survey_mode = True
    m.plots[3].state = m.BARE
    game_env.select(3)
    m.hotkey_clear_selected()
    assert "Survey mode is on" in _said(game_env)


def test_a_key_that_works_does_not_also_complain(game_env):
    m = game_env.module
    make_mature(m, 5)
    game_env.select(5)
    assert m.hotkey_clear_selected() is True
    assert "cannot" not in _said(game_env) and "already" not in _said(game_env)
    assert "Cleared F1" in _said(game_env)


def test_a_repeated_message_still_changes_the_live_region_text(game_env):
    m = game_env.module
    m.plots[3].state = m.BARE
    game_env.select(3)
    m.hotkey_clear_selected()
    first = game_env.elements["sr-announcer"].innerText
    m.hotkey_clear_selected()
    second = game_env.elements["sr-announcer"].innerText
    assert first != second and first.replace("​", "") == second.replace("​", "")


def test_the_cursor_ring_and_the_hotkeys_are_in_the_page():
    css = (ROOT / "style.css").read_text()
    assert ".plot-grid .plot-tile:focus-visible" in css and "outline: 3px solid" in css
    for page in ("index.html", "pc.html"):
        html = (ROOT / page).read_text()
        assert 'id="sr-announcer"' in html and 'aria-live="polite"' in html
        assert "hotkey_clear_selected" in html and "hotkey_replant_selected" in html and "hotkey_clear_cut_selected" in html
