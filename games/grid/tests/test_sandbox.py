"""Z-18: Grid's practice sandbox. The rules under test: entering and leaving never changes the real
game (get_state() is byte-identical), a save made while the sandbox is on is the real game, nothing in
the sandbox earns an achievement or touches the career or storage, and the sandbox grid cannot fail."""
import copy
import json
import sys
from pathlib import Path

import pytest

GAME_DIR = Path(__file__).resolve().parent.parent
PAGES = ["index.html", "pc.html"]


class FakeStorage:
    def __init__(self):
        self.data = {}
        self.writes = []

    def getItem(self, key):
        return self.data.get(key)

    def setItem(self, key, value):
        self.writes.append(key)
        self.data[key] = value


def dump(data):
    return json.dumps(data, sort_keys=True)


def play_real_game(env):
    """A real run with some history: a mixed fleet, a few rounds, a shadow twin, a spent career point."""
    g = env.module
    g.state.funds += 5000
    for plant in ("coal", "coal", "gas", "solar", "solar", "wind", "nuclear", "hydro", "battery"):
        env.build(plant)
    for _ in range(4):
        env.advance_round()
    env.maintain("coal")
    g.set_shadow_scenario("greenfield")
    g.record_shadow_action("build", "coal")
    g.real_grid_choice = None
    g.career["points"] = 3
    return g


def test_it_starts_off(game_env):
    g = game_env.module
    assert g.sandbox_is_active() is False
    assert g.sandbox_active is False
    assert g.sandbox_leave() is True  # leaving when not in it is a harmless no-op


def test_enter_then_leave_leaves_get_state_byte_identical(game_env):
    g = play_real_game(game_env)
    before = dump(g.get_state())
    real_state = g.state
    assert g.sandbox_enter() is True
    assert g.sandbox_is_active() is True
    assert g.state is not real_state
    assert g.sandbox_leave() is True
    assert g.sandbox_is_active() is False
    assert g.state is real_state, "the very same real grid object is back"
    assert dump(g.get_state()) == before


def test_playing_hard_in_the_sandbox_never_reaches_the_real_game(game_env):
    g = play_real_game(game_env)
    before = dump(g.get_state())
    career_before = copy.deepcopy(g.career)
    g.sandbox_enter()
    for plant in ("coal", "gas", "solar", "wind", "battery", "hydro", "nuclear"):
        for _ in range(3):
            game_env.build(plant)
    for _ in range(15):
        game_env.advance_round()
    game_env.retire("coal")
    game_env.maintain("gas")
    game_env.invest_demand_response()
    g.set_shadow_scenario("coal_legacy")
    g.record_shadow_action("build", "gas")
    g.info_page_open = not g.info_page_open
    g.real_grid_choice = "germany" if "germany" in g.REAL_GRIDS else next(iter(g.REAL_GRIDS))
    g.sandbox_leave()
    assert dump(g.get_state()) == before
    assert g.career == career_before


def test_get_state_while_in_the_sandbox_is_the_real_game(game_env):
    g = play_real_game(game_env)
    before = dump(g.get_state())
    g.sandbox_enter()
    game_env.build("solar")
    game_env.advance_round()
    assert dump(g.get_state()) == before
    assert g.get_state()["round_number"] == g._sandbox_real["state"].round_number
    assert g.state.round_number == 2 and g.get_state()["round_number"] != 2


def test_a_save_made_in_the_sandbox_restores_the_real_game_not_the_sandbox(game_env):
    g = play_real_game(game_env)
    real_round = g.state.round_number
    real_plants = dict(g.state.plant_counts)
    g.sandbox_enter()
    for _ in range(9):
        game_env.advance_round()
    saved = json.loads(json.dumps(g.get_state()))      # what the save widget would store
    g.sandbox_leave()
    game_env.advance_round()                              # move the real game on
    assert g.state.round_number == real_round + 1
    assert g.load_state(saved) is True
    assert g.state.round_number == real_round
    assert g.state.plant_counts == real_plants
    assert saved["round_number"] == real_round


def test_loading_a_save_while_in_the_sandbox_leaves_it_and_lands_in_the_real_game(game_env):
    g = play_real_game(game_env)
    saved = json.loads(json.dumps(g.get_state()))
    g.sandbox_enter()
    game_env.build("solar")
    assert g.load_state(saved) is True
    assert g.sandbox_is_active() is False
    assert isinstance(g.state, g.GridState) and not getattr(g.state, "sandbox", False)
    assert dump(g.get_state()) == dump(saved)


def test_nothing_in_the_sandbox_earns_an_achievement(game_env):
    g = game_env.module
    assert g.achievement_ids_earned() == []
    g.sandbox_enter()
    g.state.funds = g.SANDBOX_FUNDS
    for plant in g.PLANT_TYPES:
        game_env.build(plant)
    for _ in range(25):
        game_env.advance_round()
    assert g.state.total_capacity() > 0
    assert any(check() for check in g.ACHIEVEMENT_CHECKS.values()), "the sandbox grid would satisfy checks"
    assert g.achievement_ids_earned() == []
    assert g.get_state()["achievements_earned"] == []
    toast = game_env.elements["achievement-toast"]
    assert toast.hidden is True, "no unlock toast is shown in the sandbox"
    g.sandbox_leave()
    assert g.achievement_ids_earned() == []


def test_the_real_games_earned_achievements_stay_shown_and_saved_inside_the_sandbox(game_env):
    g = game_env.module
    game_env.build("solar")
    earned = g.achievement_ids_earned()
    assert earned
    g.sandbox_enter()
    assert g.achievement_ids_earned() == earned
    game_env.toggle_achievements()
    assert f"({len(earned)}/" in game_env.elements["achievements-toggle-button"].innerText
    g.sandbox_leave()
    assert g.achievement_ids_earned() == earned


def test_the_sandbox_grid_cannot_fail(game_env):
    g = game_env.module
    g.sandbox_enter()
    for _ in range(12):
        game_env.build("coal")
    # In a real game this much coal, no maintenance and the worst possible rolls break things every round.
    for _ in range(60):
        g.state.advance_round(rng=lambda: 0.0, age_rng=lambda: 0.0)
    assert g.state.event_log == [] and g.state.last_event is None
    assert g.state.last_aging_event is None and g.state.aging_breakdown_count == 0
    assert g.state.plant_counts["coal"] == 12
    assert g.state.disruption_probability() == 0.0
    assert g.state.funds >= g.SANDBOX_FUNDS
    assert g.state.grant_offer is None


def test_the_same_play_does_fail_in_the_real_game(game_env):
    """The control for the test above: the sandbox, not the setup, is what removes the failures."""
    g = game_env.module
    g.state.funds = 100000
    for _ in range(12):
        game_env.build("coal")
    for _ in range(60):
        g.state.advance_round(rng=lambda: 0.0, age_rng=lambda: 0.0)
    assert g.state.event_log
    assert g.state.plant_counts["coal"] < 12


def test_funds_are_unlimited_and_shown_as_such(game_env):
    g = game_env.module
    g.sandbox_enter()
    assert game_env.elements["funds-display"].innerText == "Funds: unlimited (sandbox)"
    for _ in range(40):
        game_env.build("nuclear")
    assert g.state.plant_counts["nuclear"] == 40
    assert g.state.funds >= g.SANDBOX_FUNDS
    assert game_env.elements["nuclear-build-button"].disabled is False
    g.sandbox_leave()
    assert game_env.elements["funds-display"].innerText.startswith("Funds: ")
    assert "unlimited" not in game_env.elements["funds-display"].innerText


def test_every_tool_is_unlocked(game_env):
    g = game_env.module
    assert g.state.perks == set()
    g.sandbox_enter()
    assert g.state.perks == set(g.CAREER_UNLOCK_ORDER)
    assert g.state.peek_unlocked()
    assert g.set_loadout("old_coal_contract") is True
    assert g.state.start_option == "old_coal_contract" and g.state.plant_counts["coal"] >= g.OLD_COAL_CONTRACT_PLANTS
    assert g.set_loadout("not_a_loadout") is False
    select = game_env.elements["start-option-select"]
    assert select.disabled is False
    g.sandbox_leave()
    assert g.state.perks == set() and g.career["loadout"] is None


def test_the_scenario_can_be_changed_at_any_time_in_the_sandbox_only(game_env):
    g = game_env.module
    game_env.build("coal")
    game_env.advance_round()
    assert game_env.elements["scenario-toggle-button"].disabled is True
    g.sandbox_enter()
    for _ in range(3):
        game_env.advance_round()
    button = game_env.elements["scenario-toggle-button"]
    assert button.disabled is False
    before = g.state.scenario
    button.dispatch("click", None)
    assert g.state.scenario != before
    assert g.state.round_number == 1, "a new scenario starts the practice grid over"
    assert isinstance(g.state, g.SandboxGridState)
    g.sandbox_leave()
    assert game_env.elements["scenario-toggle-button"].disabled is True


def test_the_emergency_scenario_cannot_be_missed(game_env):
    g = game_env.module
    g.sandbox_enter()
    while g.state.scenario != "emergency":
        game_env.elements["scenario-toggle-button"].dispatch("click", None)
    assert g.state.emergency["status"] == "active"
    for _ in range(40):
        game_env.advance_round()
        assert g.state.emergency["status"] in ("active", "stabilized")
    assert g.state.emergency["rounds_left"] == g.EMERGENCY_ROUNDS


def test_the_sandbox_never_touches_the_career_or_browser_storage(game_env):
    g = game_env.module
    storage = FakeStorage()
    sys.modules["js"].localStorage = storage
    g.career["points"] = 6
    g.save_career_to_storage()
    assert storage.writes, "control: outside the sandbox the career is stored"
    storage.writes.clear()
    g.sandbox_enter()
    for _ in range(8):
        game_env.advance_round()
    assert g.finish_run() is None
    assert g.unlock_career_perk("seed_capital") is False
    assert g.import_career_from_text(json.dumps({"runs": 9, "points": 99})) is False
    g.reset_career()
    game_env.elements["career-finish-button"].dispatch("click", None)
    g.save_career_to_storage()
    assert storage.writes == []
    assert g.career["points"] == 6 and g.career["runs"] == 0 and g.career["unlocked"] == []
    g.sandbox_leave()
    assert g.career["points"] == 6


def test_a_finished_sandbox_run_does_not_bank_anything_even_on_the_career_panel(game_env):
    g = game_env.module
    g.sandbox_enter()
    for _ in range(8):
        game_env.advance_round()
    game_env.toggle_career()
    assert game_env.elements["career-finish-button"].disabled is True
    assert g.career["runs"] == 0


def test_no_comparison_request_and_a_labelled_copy_result(game_env):
    g = game_env.module
    calls = []
    sys.modules["js"].window = type("W", (), {"gridCompare": staticmethod(lambda *a: calls.append(a)),
                                              "NoyvjSandbox": None})()
    game_env.toggle_summary_panel()
    assert calls, "control: the real game asks for the comparison"
    calls.clear()
    g.sandbox_enter()
    g.update_summary_panel()
    assert calls == []
    assert g.copy_result_fields()["game"] == "Grid (practice sandbox)"
    g.sandbox_leave()
    assert g.copy_result_fields()["game"] == "Grid"


def test_the_page_script_is_told_when_the_sandbox_changes_by_itself(game_env):
    g = game_env.module
    syncs = []
    shared = type("S", (), {"sync": staticmethod(lambda: syncs.append(g.sandbox_active))})()
    sys.modules["js"].window = type("W", (), {"NoyvjSandbox": shared})()
    saved = json.loads(json.dumps(g.get_state()))
    g.sandbox_enter()
    g.load_state(saved)
    assert syncs == [False]


def test_entering_twice_keeps_the_first_real_snapshot(game_env):
    g = play_real_game(game_env)
    before = dump(g.get_state())
    g.sandbox_enter()
    game_env.build("solar")
    assert g.sandbox_enter() is True
    g.sandbox_leave()
    assert dump(g.get_state()) == before


def test_auto_advance_works_in_the_sandbox(game_env):
    g = game_env.module
    g.sandbox_enter()
    game_env.build("coal")
    game_env.elements["auto-advance-button"].dispatch("click", None)
    assert g.state.round_number == 1 + g.AUTO_ADVANCE_ROUNDS


@pytest.mark.parametrize("name", PAGES)
def test_both_pages_carry_the_toggle_the_stylesheet_and_the_script(name):
    html = (GAME_DIR / name).read_text(encoding="utf-8")
    assert html.count('id="sandbox-toggle-button"') == 1
    assert 'data-sandbox-toggle' in html
    assert html.count('<link rel="stylesheet" href="../../shared/sandbox-mode.css">') == 1
    assert html.count('<script src="../../shared/sandbox-mode.js" data-game-id="grid"></script>') == 1
    head = html[: html.index("</head>")]
    assert head.index("sandbox-mode.css") < head.index("shared/a11y.css")
    # the script comes after the save widget so it can read the game's functions at click time
    assert html.index("shared/save-widget.js") < html.index("shared/sandbox-mode.js")


def test_the_desktop_menu_lists_the_toggle_under_game():
    cfg = json.loads((GAME_DIR / "pc-config.json").read_text(encoding="utf-8"))
    game = [g for g in cfg["toolbar"]["menu"] if g["heading"] == "Game"][0]
    assert "sandbox-toggle-button" in game["ids"]


def test_the_python_functions_the_shared_script_calls_exist(game_env):
    g = game_env.module
    for name in ("sandbox_enter", "sandbox_leave", "sandbox_is_active"):
        assert callable(getattr(g, name))
