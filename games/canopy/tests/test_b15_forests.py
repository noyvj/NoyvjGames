"""B-15: named local forests. The shared save widget keeps up to three forests per browser (each with its own save code
and its own remembered species choice); the game supplies the two functions it calls, start_new_forest() and
after_forest_switch(), and the page hands the widget its hook before the widget loads."""

import json
import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
INDEX = (GAME_DIR / "index.html").read_text(encoding="utf-8")
PC = (GAME_DIR / "pc.html").read_text(encoding="utf-8")


def _hook(html):
    m = re.search(r"window\.NoyvjSaveProfiles = \{(.*?)\n    \};", html, re.S)
    assert m, "the page must define window.NoyvjSaveProfiles"
    return m.group(1), m.start()


# ---- the hook on both pages ---------------------------------------------------------------------------------------

def test_both_pages_define_the_hook_before_the_save_widget_loads(game_env):
    for html in (INDEX, PC):
        body, start = _hook(html)
        assert start < html.index('shared/save-widget.js'), "the widget reads the hook as it loads"
        assert html.count('shared/save-widget.js') == 1
        assert 'noun: "forest"' in body and 'defaultName: "My forest"' in body
        assert 'start_new_forest' in body and 'after_forest_switch' in body


def test_the_hook_lists_exactly_the_keys_the_game_marks_as_per_forest(game_env):
    m = game_env.module
    for html in (INDEX, PC):
        body, _ = _hook(html)
        keys = json.loads(re.search(r"gameKeys: (\[.*?\])", body).group(1))
        assert tuple(keys) == m.FOREST_PROFILE_KEYS == (m.SPECIES_CHOICE_KEY,)


def test_the_two_functions_the_hook_calls_exist_on_the_module(game_env):
    m = game_env.module
    assert callable(m.start_new_forest) and callable(m.after_forest_switch)


# ---- start_new_forest -----------------------------------------------------------------------------------------------

def test_a_new_forest_is_the_plain_starting_game(game_env):
    m = game_env.module
    game_env.change_difficulty("ranger")
    game_env.change_grid_size("large")
    game_env.change_pace("frequent")
    game_env.tick(8)
    game_env.select(0)
    game_env.clear()
    assert m.current_difficulty == "ranger" and m.current_grid_size == "large" and m.total_income > 0

    assert m.start_new_forest() is True

    assert m.current_difficulty == m.DIFFICULTY_NORMAL and m.current_grid_size == "normal"
    assert m.current_pace == m.PACE_NORMAL and m.current_challenge == m.CHALLENGE_NONE
    assert m.current_scenario == m.SCENARIO_NONE and m.current_level is None
    assert m.current_layout is None and m.current_expedition is None
    assert m.total_income == 0.0 and len(m.plots) == 36 and m.forest_tick == 0
    for element_id, value in (("difficulty-select", "normal"), ("grid-size-select", "normal"), ("request-pace-select", "normal")):
        assert game_env.elements[element_id].value == value


def test_a_new_forest_drops_a_running_level_and_challenge(game_env):
    m = game_env.module
    m.start_level("wren_hollow", force=True)
    assert m.current_level == "wren_hollow"
    m.start_new_forest()
    assert m.current_level is None
    game_env.change_challenge("pacifist")
    assert m.current_challenge == "pacifist"
    m.start_new_forest()
    assert m.current_challenge == m.CHALLENGE_NONE


def test_a_new_forest_leaves_the_browsers_collection_alone(game_env):
    m = game_env.module
    m.levels_state = {"done": ["wren_hollow"], "best": {"wren_hollow": {"ticks": 55}}}
    before_levels = json.dumps(m.levels_state, sort_keys=True, default=str)
    before_vault = (list(m.vault_owned), dict(m.vault_meta))
    game_env.tick(6)
    game_env.select(0)
    game_env.clear()
    best = dict(m.personal_best)
    m.start_new_forest()
    assert json.dumps(m.levels_state, sort_keys=True, default=str) == before_levels
    assert (list(m.vault_owned), dict(m.vault_meta)) == before_vault
    assert m.personal_best == best


# ---- difficulty and grid size ride inside each forest's own save ------------------------------------------------------

def test_each_forest_keeps_its_own_difficulty_and_grid_size_through_save_and_load(game_env):
    m = game_env.module
    game_env.change_difficulty("ranger")
    game_env.change_grid_size("small")
    game_env.tick(5)
    ranger_forest = json.loads(json.dumps(m.get_state()))
    assert ranger_forest["current_difficulty"] == "ranger" and ranger_forest["current_grid_size"] == "small"

    m.start_new_forest()                      # the other forest: plain game, then played its own way
    game_env.change_difficulty("wildfire")
    game_env.tick(3)
    wildfire_forest = json.loads(json.dumps(m.get_state()))
    assert wildfire_forest["current_difficulty"] == "wildfire" and wildfire_forest["current_grid_size"] == "normal"

    m.load_state(ranger_forest)               # switching back
    assert m.current_difficulty == "ranger" and m.current_grid_size == "small" and len(m.plots) == 16
    assert game_env.elements["difficulty-select"].value == "ranger" and game_env.elements["grid-size-select"].value == "small"
    m.load_state(wildfire_forest)
    assert m.current_difficulty == "wildfire" and m.current_grid_size == "normal" and len(m.plots) == 36


# ---- the remembered species choice is the per-forest browser setting ------------------------------------------------

def test_after_a_switch_the_species_choice_is_read_again_and_shown(game_env):
    m = game_env.module
    game_env.local_storage.setItem(m.SPECIES_CHOICE_KEY, "oak")        # the widget wrote the opened forest's value
    assert m.species_choice == m.SPECIES_STANDARD
    assert m.after_forest_switch() is True
    assert m.species_choice == "oak" and game_env.elements["species-select"].value == "oak"
    game_env.local_storage.removeItem(m.SPECIES_CHOICE_KEY)            # a new forest has none
    m.after_forest_switch()
    assert m.species_choice == m.SPECIES_STANDARD and game_env.elements["species-select"].value == m.SPECIES_STANDARD


def test_a_bad_species_value_in_storage_falls_back_to_standard(game_env):
    m = game_env.module
    for bad in ("not-a-species", "mangrove", "", "<b>"):
        game_env.local_storage.setItem(m.SPECIES_CHOICE_KEY, bad)
        m.after_forest_switch()
        assert m.species_choice == m.SPECIES_STANDARD


def test_changing_the_species_writes_the_key_the_widget_carries(game_env):
    m = game_env.module
    select = game_env.elements["species-select"]
    select.value = "pine"

    class _Event:
        target = select

    m.on_species_change(_Event())
    assert game_env.local_storage.getItem(m.FOREST_PROFILE_KEYS[0]) == "pine"
