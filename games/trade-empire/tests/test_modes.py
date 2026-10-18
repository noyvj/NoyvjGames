"""GN-17: the Modes screen, the pilot for "modes as levels". The rules under test: the game modes are an ordered ladder
on the shared level select with the core game first; EVERY rung is open from the start (no gating of any kind); the
first rung not tried yet carries the "Next suggested mode" marker; what counts as tried is read from what the real game
already records (so nothing new is saved, and the answer is the same inside a puzzle, a crisis or the sandbox); and the
screen is reachable from the Classic toolbar and the Desktop Menu."""
import json
import sys
import types
from pathlib import Path

import pytest

from .pagefiles import notes_text

GAME_DIR = Path(__file__).resolve().parent.parent


def dump(data):
    return json.dumps(data, sort_keys=True)


class FakeLevelSelect:
    def __init__(self):
        self.created = []
        self.levels = None
        self.state = None
        self.opened = 0

    def create(self, options):
        self.created.append(options)
        parent = self

        class Screen:
            def setState(self, state):
                parent.state = state

            def setLevels(self, levels):
                parent.levels = levels

            def open(self):
                parent.opened += 1

        return Screen()


@pytest.fixture
def screen():
    fake = FakeLevelSelect()
    sys.modules["js"].window = types.SimpleNamespace(NoyvjLevels=types.SimpleNamespace(create=fake.create))
    sys.modules["js"].Object = types.SimpleNamespace(fromEntries=None)
    sys.modules["pyodide.ffi"].to_js = lambda value, dict_converter=None: value
    yield fake
    del sys.modules["js"].window
    del sys.modules["js"].Object
    del sys.modules["pyodide.ffi"].to_js


def automate_a_ship(m):
    m.total_profit = 1000
    m.ships["1"].automated = True


# --- the ladder -----------------------------------------------------------------------------------------------------

def test_the_ladder_starts_with_the_core_game_then_the_modes_gentlest_first(game_env):
    m = game_env.module
    assert m.MODE_IDS == ("core", "expeditions", "chain", "crises", "blackout", "sandbox")
    assert m.MODES[0]["kind"] == "level" and all(mode["kind"] == "mode" for mode in m.MODES[1:])
    assert len(set(m.MODE_IDS)) == len(m.MODES)


def test_every_rung_has_a_one_line_description_of_what_it_adds(game_env):
    m = game_env.module
    for mode in m.MODES:
        assert mode["title"].strip() and 40 <= len(mode["blurb"]) <= 200 and "\n" not in mode["blurb"]
        if mode["id"] != "core":
            assert mode["blurb"].startswith("Adds: "), mode["id"]


def test_the_fifth_rung_is_a_mode_as_the_level_select_convention_asks(game_env):
    m = game_env.module
    assert m.MODES[4]["kind"] in ("mode", "mechanic")


def test_no_rung_is_gated_in_any_way(game_env):
    m = game_env.module
    for level in m.modes_levels_list():
        assert not (set(level) & {"requires", "requires_count", "unlock_text"}), level["id"]
    # even a brand-new game offers every mode: starting each one is possible straight away
    for mode_id in m.MODE_IDS:
        assert m.modes_start(mode_id) is True
        m.chain_leave()
        m.sandbox_leave()


def test_the_levels_handed_to_the_screen_are_the_ladder_in_order(game_env):
    m = game_env.module
    levels = m.modes_levels_list()
    assert [level["id"] for level in levels] == list(m.MODE_IDS)
    assert [level["title"] for level in levels] == [mode["title"] for mode in m.MODES]


# --- what counts as tried, and the suggested marker ---------------------------------------------------------------

def test_a_new_game_has_tried_nothing_and_suggests_the_core_game(game_env):
    m = game_env.module
    assert m.modes_done_ids() == [] and m.modes_next_suggested() == "core"


def test_each_rung_counts_as_tried_from_what_the_game_already_records(game_env):
    m = game_env.module
    automate_a_ship(m)
    assert m.modes_done_ids() == ["core"] and m.modes_next_suggested() == "expeditions"
    m.records["expeditions"] = 1
    assert m.modes_done_ids() == ["core", "expeditions"] and m.modes_next_suggested() == "chain"
    m.records["chain_best"]["first_delivery"] = {"units": 30, "ships": 2}
    assert m.modes_next_suggested() == "crises"
    m.records["crisis_best"]["grain_famine"] = {"medal": "bronze", "ticks": 90}
    assert m.modes_next_suggested() == "blackout"
    m.blackout_enabled = True
    assert m.modes_done_ids() == ["core", "expeditions", "chain", "crises", "blackout"]
    assert m.modes_next_suggested() == "sandbox", "the last rung is free play and is never marked tried"


def test_blackout_counts_from_a_dark_run_or_bought_intel_too(game_env):
    m = game_env.module
    m.records["dark_runs"] = 1
    assert "blackout" in m.modes_done_ids()
    m.records["dark_runs"] = 0
    m.blackout_bought.add("feed")
    assert "blackout" in m.modes_done_ids()


def test_the_order_is_a_path_not_a_gate(game_env):
    m = game_env.module
    m.records["chain_best"]["first_delivery"] = {"units": 30, "ships": 2}  # tried out of order
    assert m.modes_done_ids() == ["chain"]
    assert m.modes_next_suggested() == "core"


def test_exactly_one_rung_carries_the_next_suggested_marker(game_env):
    m = game_env.module
    for setup in (lambda: None, lambda: automate_a_ship(m)):
        setup()
        marked = [lv for lv in m.modes_levels_list() if lv["blurb"].startswith("Next suggested mode. ")]
        assert [lv["id"] for lv in marked] == [m.modes_next_suggested()]
    assert "Next suggested mode" not in m.MODES[1]["blurb"], "the data itself carries no marker"


def test_the_answer_is_the_same_inside_a_puzzle_a_crisis_or_the_sandbox(game_env):
    m = game_env.module
    automate_a_ship(m)
    m.records["expeditions"] = 2
    m.records["chain_best"]["first_delivery"] = {"units": 30, "ships": 2}
    m.blackout_enabled = True
    expected = (m.modes_done_ids(), m.modes_next_suggested())
    assert expected[0] == ["core", "expeditions", "chain", "blackout"]
    m.chain_enter("thin_seam")
    assert (m.modes_done_ids(), m.modes_next_suggested()) == expected
    m.crisis_enter("grain_famine")
    assert (m.modes_done_ids(), m.modes_next_suggested()) == expected
    m.sandbox_leave()
    m.sandbox_enter()
    assert (m.modes_done_ids(), m.modes_next_suggested()) == expected
    m.sandbox_leave()
    assert (m.modes_done_ids(), m.modes_next_suggested()) == expected


def test_looking_at_the_modes_changes_nothing_in_the_save(game_env):
    m = game_env.module
    before = dump(m.get_state())
    m.modes_done_ids()
    m.modes_levels_list()
    m.render_modes()
    assert dump(m.get_state()) == before
    assert not any("mode" in key for key in m.get_state()), "no new save key"


# --- starting a rung ------------------------------------------------------------------------------------------------

def test_the_core_rung_only_points_at_the_main_controls(game_env):
    m = game_env.module
    before = dump(m.get_state())
    assert m.modes_start("core")
    assert "load a ship" in game_env.elements["notice-toast"].innerText
    assert dump(m.get_state()) == before and not m.sandbox_active


def test_expeditions_and_crises_open_the_fleet_lab(game_env):
    m = game_env.module
    for mode_id in ("expeditions", "crises"):
        m.lab_open = False
        m.modes_start(mode_id)
        assert m.lab_open is True and game_env.elements["lab-panel"].hidden is False


def test_chain_builder_opens_its_window(game_env):
    m = game_env.module
    m.modes_start("chain")
    assert m.chain_open is True and game_env.elements["chain-panel"].hidden is False
    assert m.chain_active is None, "it opens the window; the player picks the puzzle"


def test_blackout_is_never_switched_on_for_the_player(game_env):
    m = game_env.module
    m.modes_start("blackout")
    assert m.blackout_enabled is False
    assert "asks first" in game_env.elements["notice-toast"].innerText


def test_the_sandbox_rung_starts_the_practice_sandbox_and_it_can_be_left(game_env):
    m = game_env.module
    before = dump(m.get_state())
    m.modes_start("sandbox")
    assert m.sandbox_is_active()
    m.sandbox_leave()
    assert dump(m.get_state()) == before


def test_an_unknown_rung_does_nothing(game_env):
    m = game_env.module
    for bad in ("nope", None, 3):
        assert m.modes_start(bad) is False


# --- the screen and the button ---------------------------------------------------------------------------------------

def test_the_button_builds_the_screen_once_and_opens_it(game_env, screen):
    m = game_env.module
    game_env.elements["modes-open-button"].dispatch("click", None)
    assert screen.opened == 0, "it opens a moment later, after the Desktop Menu has closed itself and returned focus"
    game_env.timers.flush()
    assert screen.opened == 1 and len(screen.created) == 1
    options = screen.created[0]
    assert options["domId"] == "modes-select" and options["title"] == "Game modes"
    assert [lv["id"] for lv in options["levels"]] == list(m.MODE_IDS)
    assert options["state"] == {"done": [], "best": {}}
    game_env.elements["modes-open-button"].dispatch("click", None)
    game_env.timers.flush()
    assert screen.opened == 2 and len(screen.created) == 1


def test_choosing_a_rung_on_the_screen_takes_you_there(game_env, screen):
    m = game_env.module
    game_env.elements["modes-open-button"].dispatch("click", None)
    game_env.timers.flush()
    screen.created[0]["onStart"]("chain")
    assert m.chain_open is True


def test_the_screen_is_refreshed_with_the_current_progress_each_time_it_opens(game_env, screen):
    m = game_env.module
    game_env.elements["modes-open-button"].dispatch("click", None)
    assert screen.state == {"done": [], "best": {}}
    automate_a_ship(m)
    game_env.elements["modes-open-button"].dispatch("click", None)
    assert screen.state["done"] == ["core"]
    assert screen.levels[1]["blurb"].startswith("Next suggested mode. ")


def test_the_button_tooltip_names_the_next_suggested_mode_and_follows_progress(game_env):
    m = game_env.module
    m.render()
    title = game_env.elements["modes-open-button"].title
    assert "Next suggested mode: The core game." in title and "Every one is open" in title
    automate_a_ship(m)
    m.render()
    assert "Next suggested mode: Expeditions." in game_env.elements["modes-open-button"].title


def test_without_the_shared_script_the_button_is_harmless(game_env):
    game_env.elements["modes-open-button"].dispatch("click", None)  # no window.NoyvjLevels in the fake page


@pytest.mark.parametrize("name", ["index.html", "pc.html"])
def test_both_pages_carry_the_button_and_the_shared_script(name):
    html = (GAME_DIR / name).read_text(encoding="utf-8")
    assert 'id="modes-open-button"' in html and "shared/level-select.js" in html


def test_the_desktop_menu_lists_modes_first_under_empire():
    cfg = json.loads((GAME_DIR / "pc-config.json").read_text(encoding="utf-8"))
    empire = next(g for g in cfg["toolbar"]["menu"] if g["heading"] == "Empire")
    assert empire["ids"][0] == "modes-open-button"


def test_the_guideline_is_written_up_in_the_game_notes():
    notes = notes_text()
    assert "## Modes as levels" in notes
