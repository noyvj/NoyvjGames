"""GB batch 3 (W-1): the level select data, starting and finishing levels, the saved `levels` key,
the Python twin of the shared level state rules, and the bridge to shared/level-select.js."""

import json
import sys
import types
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent.parent
LEVELS_JSON = json.loads((HERE / "levels.json").read_text(encoding="utf-8"))


def _fake_window(levels):
    """Installs a fake `window` with a recording NoyvjLevels into the fake js module (and the two helpers
    game.py uses to hand Python data to JS), the way a real page would offer them."""
    sys.modules["js"].window = types.SimpleNamespace(NoyvjLevels=levels)
    sys.modules["js"].Object = types.SimpleNamespace(fromEntries=None)
    sys.modules["pyodide.ffi"].to_js = lambda value, **_kw: value


class RecordingLevels:
    def __init__(self):
        self.configured = []
        self.states = []

    def configure(self, cfg):
        self.configured.append(cfg)

    def setState(self, state):  # noqa: N802 -- the JS API's name
        self.states.append(state)


# --- the data ----------------------------------------------------------------------------------------------

def test_levels_json_matches_the_python_specs(game_env):
    m = game_env.module
    ids = [level["id"] for level in LEVELS_JSON["levels"]]
    assert ids == m.LEVEL_ORDER
    for entry in LEVELS_JSON["levels"]:
        spec = m.LEVEL_SPECS[entry["id"]]
        assert entry["title"] == spec["title"]
        assert entry.get("requires", []) == spec.get("requires", [])
        assert entry.get("requires_count", 0) == spec.get("requires_count", 0)
        assert entry.get("unlock_text") == spec.get("unlock_text")
        assert entry.get("better") == "lower"
        assert entry.get("unit") == spec.get("unit", "ticks")


def test_every_fifth_level_is_a_mode_or_a_mechanic(game_env):
    """The Python twin of NoyvjLevels.logic.audit: every fifth entry is not a plain level, and every
    `requires` id exists."""
    levels = LEVELS_JSON["levels"]
    for position, entry in enumerate(levels, start=1):
        if position % 5 == 0:
            assert entry["kind"] in ("mode", "mechanic"), (position, entry["id"])
    known = {entry["id"] for entry in levels}
    for entry in levels:
        for needed in entry.get("requires", []):
            assert needed in known
    assert len(levels) >= 15
    assert [levels[i]["id"] for i in (4, 9, 14)] == ["poacher_patrol", "storm_front", "spirits_walk"]


def test_the_four_challenge_runs_are_levels(game_env):
    m = game_env.module
    challenges = {spec["challenge"] for spec in m.LEVEL_SPECS.values() if "challenge" in spec}
    assert challenges == set(m.CHALLENGE_SPECS)


def test_specs_only_use_known_presets(game_env):
    m = game_env.module
    for level_id, spec in m.LEVEL_SPECS.items():
        assert spec.get("grid", "normal") in m.GRID_SIZE_PRESETS, level_id
        assert spec.get("difficulty", m.DIFFICULTY_NORMAL) in m.DEGRADE_PER_CLEAR_BY_DIFFICULTY, level_id
        assert spec.get("pace", m.PACE_NORMAL) in m.REQUEST_PACE_FACTOR, level_id
        assert spec.get("challenge", m.CHALLENGE_NONE) in (m.CHALLENGE_NONE, *m.CHALLENGE_SPECS), level_id
        assert spec["goal"], level_id


def test_the_level_list_is_not_a_dead_end(game_env):
    """Every level can be unlocked by completing the others in order (no cycles, no impossible counts)."""
    m = game_env.module
    done = []
    for _ in range(len(m.LEVEL_ORDER)):
        m.levels_state["done"] = list(done)
        nxt = next((i for i in m.LEVEL_ORDER if i not in done and m.level_lock_reason(i) == ""), None)
        assert nxt is not None, f"stuck with {done}"
        done.append(nxt)
    assert sorted(done) == sorted(m.LEVEL_ORDER)


# --- locks ------------------------------------------------------------------------------------------------------

def test_lock_reasons_follow_the_shared_wording(game_env):
    m = game_env.module
    assert m.level_lock_reason("wren_hollow") == ""
    assert m.level_lock_reason("fern_glade") == "Complete Wren Hollow first"
    assert m.level_lock_reason("poacher_patrol") == "Complete any 3 levels first"
    m.levels_state["done"] = ["wren_hollow"]
    assert m.level_lock_reason("fern_glade") == ""
    assert m.level_lock_reason("nonsense") == "Unknown level"


def test_a_locked_level_will_not_start(game_env):
    m = game_env.module
    assert m.start_level("fern_glade") is False
    assert m.current_level is None
    assert m.start_level("nonsense") is False
    assert m.start_level("fern_glade", force=True) is True
    assert m.current_level == "fern_glade"


# --- starting ---------------------------------------------------------------------------------------------------

def test_starting_a_level_applies_its_presets(game_env):
    m = game_env.module
    m.start_level("fern_glade", force=True)
    assert m.current_grid_size == "small" and len(m.plots) == 16
    m.start_level("ranger_trail", force=True)
    assert m.current_difficulty == m.DIFFICULTY_RANGER and m.current_grid_size == "normal"
    m.start_level("quiet_valley", force=True)
    assert m.current_pace == m.PACE_RELAXED and m.current_difficulty == m.DIFFICULTY_NORMAL
    m.start_level("pacifist", force=True)
    assert m.current_challenge == m.CHALLENGE_PACIFIST
    m.start_level("wren_hollow", force=True)
    assert m.current_challenge == m.CHALLENGE_NONE and m.current_pace == m.PACE_NORMAL
    assert m.forest_tick == 0 and m.level_ticks == 0


def test_the_selects_show_the_level_presets(game_env):
    m = game_env.module
    m.start_level("birch_flats", force=True)
    assert game_env.elements["grid-size-select"].value == "large"


def test_starting_a_level_throws_away_the_session_it_replaces(game_env):
    m = game_env.module
    game_env.tick(5)
    m.total_income = 99.0
    m.start_level("wren_hollow", force=True)
    assert m.total_income == 0.0 and m.forest_tick == 0


def test_reset_session_retries_the_level_but_a_select_leaves_it(game_env):
    m = game_env.module
    m.start_level("quiet_valley", force=True)
    game_env.tick(3)
    game_env.reset_session()
    assert m.current_level == "quiet_valley" and m.level_ticks == 0 and m.current_pace == m.PACE_RELAXED
    game_env.change_pace("frequent")
    assert m.current_level is None
    m.start_level("wren_hollow", force=True)
    game_env.change_grid_size("small")
    assert m.current_level is None
    m.start_level("wren_hollow", force=True)
    game_env.change_challenge("sprint")
    assert m.current_level is None


def test_leave_level_keeps_the_forest_for_free_play(game_env):
    m = game_env.module
    m.start_level("wren_hollow", force=True)
    game_env.tick(4)
    value = m.standing_forest_value()
    assert game_env.elements["level-leave-button"].disabled is False
    game_env.elements["level-leave-button"].dispatch("click", None)
    assert m.current_level is None
    assert m.standing_forest_value() >= value
    assert game_env.elements["level-box"].hidden is True
    assert m.on_leave_level() is False


def test_a_fresh_game_shows_no_level_box(game_env):
    assert game_env.elements["level-box"].hidden is True
    assert game_env.elements["level-status"].innerText == ""


# --- completing --------------------------------------------------------------------------------------------------

def _run_until_done(env, limit=400):
    m = env.module
    for _ in range(limit):
        if m.level_done_tick is not None:
            return True
        env.tick()
    return False


def test_a_plain_level_completes_and_records_its_ticks(game_env):
    m = game_env.module
    m.start_level("wren_hollow", force=True)
    assert _run_until_done(game_env)
    assert "wren_hollow" in m.levels_state["done"]
    best = m.levels_state["best"]["wren_hollow"]
    assert best["value"] == m.level_done_tick and best["text"] == f"{m.level_done_tick} ticks"
    assert "✓ complete" in game_env.elements["level-status"].innerText
    assert any(e["kind"] == "level" and "complete" in e["text"] for e in m.forest_log)


def test_a_completed_level_does_not_complete_again_each_tick(game_env):
    m = game_env.module
    m.start_level("wren_hollow", force=True)
    _run_until_done(game_env)
    done_tick = m.level_done_tick
    count = len([e for e in m.forest_log if e["kind"] == "level" and "complete" in e["text"]])
    game_env.tick(5)
    assert m.level_done_tick == done_tick
    assert len([e for e in m.forest_log if e["kind"] == "level" and "complete" in e["text"]]) == count


def test_goal_scales_with_the_grid(game_env):
    m = game_env.module
    m.start_level("fern_glade", force=True)
    parts = m.level_goal_parts()
    assert parts[0][0].endswith(f"of {130 * 16}")


def test_a_worse_result_never_replaces_the_best(game_env):
    m = game_env.module
    assert m.record_level_result("wren_hollow", 40, "40 ticks") is True
    assert m.record_level_result("wren_hollow", 55, "55 ticks") is False
    assert m.levels_state["best"]["wren_hollow"]["value"] == 40
    assert m.record_level_result("wren_hollow", 31, "31 ticks") is True
    assert m.levels_state["best"]["wren_hollow"]["value"] == 31
    assert m.record_level_result("wren_hollow", 31, "31 ticks") is False  # a tie changes nothing
    assert m.record_level_result("nonsense", 1, "x") is False


def test_a_text_only_result_never_replaces_a_numbered_best(game_env):
    m = game_env.module
    m.record_level_result("wren_hollow", 40, "40 ticks")
    m.record_level_result("wren_hollow", None, "done")
    assert m.levels_state["best"]["wren_hollow"]["value"] == 40


def test_zero_is_a_valid_best(game_env):
    m = game_env.module
    m.record_level_result("poacher_patrol", 3, "3 missed")
    assert m.record_level_result("poacher_patrol", 0, "0 missed") is True
    assert m.levels_state["best"]["poacher_patrol"]["value"] == 0


def test_a_challenge_level_completes_when_the_challenge_does(game_env):
    m = game_env.module
    m.start_level("pacifist", force=True)
    assert _run_until_done(game_env)
    assert m.challenge_state() == m.CHALLENGE_COMPLETE
    assert "pacifist" in m.levels_state["done"]


def test_a_failed_challenge_level_stays_open(game_env):
    m = game_env.module
    m.start_level("pacifist", force=True)
    game_env.select(0)
    game_env.clear()
    game_env.tick(3)
    assert m.level_done_tick is None
    assert "failed" in game_env.elements["level-status"].innerText


def test_highland_and_wetland_levels_end_on_the_unlock(game_env):
    m = game_env.module
    m.start_level("highland_climb", force=True)
    assert _run_until_done(game_env)
    assert m.highland_unlocked
    m.start_level("wetland_reach", force=True)
    assert _run_until_done(game_env)
    assert m.wetland_unlocked


def test_busy_valley_needs_requests_answered(game_env):
    m = game_env.module
    m.start_level("busy_valley", force=True)
    for _ in range(80):
        game_env.tick()
        if m.pending_stakeholder_request is not None:
            game_env.decline_stakeholder()
        if m.level_done_tick is not None:
            break
    assert m.level_done_tick is not None
    assert m.stakeholder_grants_count + m.stakeholder_declines_count >= 3


def test_ranger_trail_needs_income_as_well_as_standing_value(game_env):
    m = game_env.module
    m.start_level("ranger_trail", force=True)
    game_env.tick(60)
    assert m.standing_forest_value() >= 80 * 36
    assert m.level_done_tick is None  # no income yet: the second half of the goal is still open
    game_env.select(0)
    m.total_income = 15 * 36
    game_env.tick()
    assert m.level_done_tick is not None


# --- progress counters ---------------------------------------------------------------------------------------------

def test_levels_progress_text(game_env):
    m = game_env.module
    assert m.levels_progress_text() == "0 of 15 levels complete"
    m.record_level_result("wren_hollow", 30, "30 ticks")
    assert m.levels_progress_text() == "1 of 15 levels complete"


# --- save state -------------------------------------------------------------------------------------------------

def test_a_fresh_game_saves_none_of_the_new_keys(game_env):
    state = game_env.module.get_state()
    for key in ("levels", "seed_vault", "level_run"):
        assert key not in state


def test_levels_and_the_running_level_round_trip(game_env):
    m = game_env.module
    m.record_level_result("wren_hollow", 30, "30 ticks")
    m.start_level("fern_glade", force=True)
    game_env.tick(7)
    state = json.loads(json.dumps(m.get_state()))
    assert state["levels"]["done"] == ["wren_hollow"]
    assert state["level_run"]["id"] == "fern_glade" and state["level_run"]["ticks"] == 7
    m.reset_session(level=None)
    m.levels_state["done"].clear()
    m.levels_state["best"].clear()
    m.load_state(state)
    assert m.levels_state["done"] == ["wren_hollow"]
    assert m.current_level == "fern_glade" and m.level_ticks == 7 and m.current_grid_size == "small"


def test_a_save_without_the_keys_loads_and_keeps_this_browsers_progress(game_env):
    m = game_env.module
    m.record_level_result("wren_hollow", 30, "30 ticks")
    state = m.get_state()
    for key in ("levels", "seed_vault", "level_run"):
        state.pop(key, None)
    m.start_level("fern_glade", force=True)
    m.load_state(state)
    assert m.current_level is None
    assert m.levels_state["done"] == ["wren_hollow"]


def test_loading_merges_progress_instead_of_losing_it(game_env):
    m = game_env.module
    m.record_level_result("wren_hollow", 50, "50 ticks")
    m.record_level_result("fern_glade", 40, "40 ticks")
    state = m.get_state()
    state["levels"] = {"done": ["wren_hollow", "birch_flats"], "best": {
        "wren_hollow": {"value": 30, "text": "30 ticks"}, "birch_flats": {"value": 33, "text": "33 ticks"}}}
    m.load_state(state)
    assert m.levels_state["done"] == ["wren_hollow", "fern_glade", "birch_flats"] or set(m.levels_state["done"]) == {
        "wren_hollow", "fern_glade", "birch_flats"}
    assert m.levels_state["best"]["wren_hollow"]["value"] == 30  # the better of the two
    assert m.levels_state["best"]["fern_glade"]["value"] == 40


@pytest.mark.parametrize("garbage", [
    None, 5, "x", [], {}, {"done": "wren_hollow"}, {"done": [1, None, {}, ["a"], "nonsense", "wren_hollow", "wren_hollow"]},
    {"done": ["wren_hollow"], "best": {"wren_hollow": "fast"}},
    {"done": ["wren_hollow"], "best": {"wren_hollow": {"value": float("nan"), "text": 4}}},
    {"done": ["wren_hollow"], "best": {"wren_hollow": {"value": True}}},
    {"done": ["wren_hollow"], "best": {"fern_glade": {"value": 3}}},
    {"done": ["wren_hollow"], "best": [1, 2]},
    {"done": ["wren_hollow"], "best": {"wren_hollow": {"value": float("inf")}}},
])
def test_garbage_levels_values_never_break_a_load(game_env, garbage):
    m = game_env.module
    state = m.get_state()
    state["levels"] = garbage
    m.load_state(state)
    clean = m.levels_state
    assert set(clean["done"]) <= set(m.LEVEL_ORDER)
    assert all(isinstance(i, str) for i in clean["done"])
    assert set(clean["best"]) <= set(clean["done"])
    for entry in clean["best"].values():
        assert set(entry) <= {"value", "text"}
        if "value" in entry:
            assert entry["value"] == entry["value"] and not isinstance(entry["value"], bool)
    game_env.tick(2)  # still plays


@pytest.mark.parametrize("garbage", [
    None, 3, "wren_hollow", [], {}, {"id": 5}, {"id": "nonsense"}, {"id": "wren_hollow", "ticks": "x", "done_tick": [1]},
    {"id": "wren_hollow", "ticks": -50, "done_tick": -3}, {"id": "wren_hollow", "ticks": float("nan")},
    {"id": "poacher_patrol", "poacher": "no"}, {"id": "storm_front", "storm": [1]}, {"id": "spirits_walk", "spirit": 7},
    {"id": "fern_glade"},  # a level that does not match the loaded settings is dropped
])
def test_garbage_level_run_never_breaks_a_load(game_env, garbage):
    m = game_env.module
    state = m.get_state()
    state["level_run"] = garbage
    m.load_state(state)
    assert m.current_level is None or m.current_level in m.LEVEL_SPECS
    assert m.level_ticks >= 0
    game_env.tick(3)


def test_a_level_run_that_disagrees_with_the_save_settings_is_dropped(game_env):
    m = game_env.module
    state = m.get_state()
    state["level_run"] = {"id": "fern_glade", "ticks": 5}  # fern_glade is small; this save is normal
    m.load_state(state)
    assert m.current_level is None


def test_a_saved_level_restores_its_mode_state(game_env):
    m = game_env.module
    m.start_level("storm_front", force=True)
    game_env.tick(9)
    state = json.loads(json.dumps(m.get_state()))
    m.start_level("wren_hollow", force=True)
    m.load_state(state)
    assert m.current_level == "storm_front"
    assert m.storm_run["next_in"] == state["level_run"]["storm"]["next_in"] == m.STORM_INTERVAL_TICKS - 9


# --- browser storage ---------------------------------------------------------------------------------------------

def test_progress_is_kept_per_browser_and_survives_a_reset(game_env):
    m = game_env.module
    m.record_level_result("wren_hollow", 30, "30 ticks")
    stored = json.loads(game_env.local_storage.getItem(m.META_STORAGE_KEY))
    assert stored["levels"]["done"] == ["wren_hollow"]
    game_env.reset_session()
    assert m.levels_state["done"] == ["wren_hollow"]


def test_start_up_reads_this_browsers_progress(game_env):
    m = game_env.module
    blob = {"levels": {"done": ["wren_hollow", "nonsense"], "best": {"wren_hollow": {"value": 33, "text": "33 ticks"}}},
            "seed_vault": {"owned": ["deep_roots", "bogus"], "best_tier": 2, "best_ach": 8}}
    game_env.local_storage.setItem(m.META_STORAGE_KEY, json.dumps(blob))
    m.levels_state = {"done": [], "best": {}}
    del m.vault_owned[:]
    m._load_meta()
    assert m.levels_state["done"] == ["wren_hollow"]
    assert m.vault_owned == ["deep_roots"] and m.vault_meta == {"best_tier": 2, "best_ach": 8}


@pytest.mark.parametrize("raw", ["", "not json", "[]", "5", '{"levels": 4, "seed_vault": "x"}', "null"])
def test_a_corrupt_browser_blob_is_ignored(game_env, raw):
    m = game_env.module
    game_env.local_storage.setItem(m.META_STORAGE_KEY, raw)
    m._load_meta()
    assert isinstance(m.levels_state["done"], list)


# --- the bridge to shared/level-select.js --------------------------------------------------------------------------

def test_the_bridge_configures_once_and_pushes_state(game_env):
    m = game_env.module
    levels = RecordingLevels()
    _fake_window(levels)
    m._levels_bridge_ready = False
    assert m._setup_levels_bridge() is True
    assert len(levels.configured) == 1
    cfg = levels.configured[0]
    assert "onStart" in cfg and cfg["state"] == {"done": [], "best": {}}
    assert m._setup_levels_bridge() is True and len(levels.configured) == 1  # idempotent
    m.record_level_result("wren_hollow", 30, "30 ticks")
    assert levels.states[-1]["done"] == ["wren_hollow"]
    cfg["onStart"]("quiet_valley", None)  # the screen's Play on a locked level does nothing in Python
    assert m.current_level is None
    cfg["onStart"]("wren_hollow", None)
    assert m.current_level == "wren_hollow"


def test_a_page_without_the_level_select_still_plays(game_env):
    m = game_env.module
    assert m._setup_levels_bridge() is False
    m.record_level_result("wren_hollow", 30, "30 ticks")  # must not raise
    game_env.tick(2)
