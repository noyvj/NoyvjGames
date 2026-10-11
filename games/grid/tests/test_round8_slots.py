"""Round-8 pass: three named local run slots (C-13)."""
import json
import sys

from .test_confirm_dialog import _install_fake_confirm_dialog
from .test_sandbox import FakeStorage


def _storage():
    storage = FakeStorage()
    sys.modules["js"].localStorage = storage
    return storage


def _select(env, index):
    env.elements["slot-select"].value = str(index)


def _click(env, name):
    env.elements[f"slot-{name}-button"].dispatch("click", None)


def _name(env, text):
    env.elements["slot-name-input"].value = text


def _build_some(env, coal=2):
    for _ in range(coal):
        env.build("coal")


def test_three_empty_slots_at_the_start_and_nothing_attached(game_env):
    _storage()
    g = game_env.module
    g.render()
    assert g.load_slots() == [None, None, None]
    assert g.slot_attached is None
    assert "No slot holds this run yet" in game_env.elements["slot-status"].innerText
    html = game_env.elements["slot-select"].innerHTML
    assert html.count("<option") == 3 and html.count("empty") == 3
    assert game_env.elements["slot-load-button"].disabled is True
    assert game_env.elements["slot-clear-button"].disabled is True


def test_save_here_stores_the_run_in_the_slot_and_attaches(game_env):
    storage = _storage()
    g = game_env.module
    _build_some(game_env)
    game_env.advance_round()
    _select(game_env, 1)
    _name(game_env, "  Coal   exit  ")
    _click(game_env, "save")
    slots = g.load_slots()
    assert slots[0] is None and slots[2] is None
    assert slots[1]["name"] == "Coal exit"
    assert slots[1]["state"]["round_number"] == 2 and slots[1]["state"]["plant_counts"]["coal"] == 2
    assert g.slot_attached == 1
    assert "slot 2" in game_env.elements["slot-status"].innerText
    assert "Slot 2: Coal exit (round 2, Standard start) (this run)" in game_env.elements["slot-select"].innerHTML
    assert g.SLOTS_STORAGE_KEY in storage.data


def test_an_attached_slot_autosaves_after_each_round(game_env):
    _storage()
    g = game_env.module
    _build_some(game_env)
    _click(game_env, "save")
    assert g.load_slots()[0]["state"]["round_number"] == 1
    game_env.advance_round()
    game_env.advance_round()
    assert g.load_slots()[0]["state"]["round_number"] == 3
    game_env.auto_advance()
    assert g.load_slots()[0]["state"]["round_number"] == g.state.round_number


def test_nothing_is_written_to_a_slot_by_itself(game_env):
    storage = _storage()
    _build_some(game_env)
    game_env.advance_round()
    game_env.advance_round()
    assert game_env.module.SLOTS_STORAGE_KEY not in storage.data


def test_switching_saves_the_current_run_first_and_loads_the_other(game_env):
    _storage()
    g = game_env.module
    _build_some(game_env, 3)
    game_env.advance_round()
    _select(game_env, 0)
    _name(game_env, "First")
    _click(game_env, "save")
    _select(game_env, 1)
    _name(game_env, "Second")
    _click(game_env, "new")          # a fresh run in slot 2; slot 1 was saved first
    assert g.slot_attached == 1
    assert g.state.round_number == 1 and g.state.plant_counts["coal"] == 0
    assert g.load_slots()[0]["state"]["plant_counts"]["coal"] == 3
    game_env.build("solar")
    game_env.advance_round()
    _select(game_env, 0)
    _click(game_env, "load")
    assert g.slot_attached == 0
    assert g.state.plant_counts["coal"] == 3 and g.state.round_number == 2
    # slot 2 got the solar run saved on the way out
    assert g.load_slots()[1]["state"]["plant_counts"]["solar"] == 1


def test_each_slot_keeps_its_own_scenario(game_env):
    _storage()
    g = game_env.module
    game_env.elements["scenario-toggle-button"].dispatch("click", None)  # coal-heavy legacy
    assert g.state.scenario == "coal_legacy"
    _select(game_env, 0)
    _click(game_env, "save")
    _select(game_env, 1)
    _click(game_env, "new")
    assert g.state.scenario == "standard"
    _select(game_env, 0)
    _click(game_env, "load")
    assert g.state.scenario == "coal_legacy" and g.state.plant_counts["coal"] == 4
    assert "Coal-heavy legacy grid" in game_env.elements["slot-select"].innerHTML


def test_loading_an_empty_slot_is_refused_with_a_reason(game_env):
    _storage()
    g = game_env.module
    _build_some(game_env)
    _select(game_env, 2)
    assert g.slot_switch_to(2) is False
    assert "empty" in g.slot_message
    assert g.state.plant_counts["coal"] == 2


def test_replacing_an_unsaved_run_asks_first_and_cancel_keeps_it(game_env):
    _storage()
    g = game_env.module
    _build_some(game_env)
    game_env.advance_round()
    _select(game_env, 0)
    _click(game_env, "save")
    # a second, unsaved run: detach by clearing the slot
    window = _install_fake_confirm_dialog()
    _click(game_env, "clear")
    window.ConfirmDialog.confirm()
    assert g.slot_attached is None
    # put a different run in slot 2, then build on an unattached run
    _build_some(game_env, 1)
    _select(game_env, 1)
    _click(game_env, "save")
    window.ConfirmDialog.calls.clear()
    g.slot_attached = None
    g.state.plant_counts["coal"] += 1
    _click(game_env, "load")
    assert window.ConfirmDialog.calls and window.ConfirmDialog.calls[-1]["id"] == "grid-slot-switch"
    assert window.ConfirmDialog.calls[-1]["allowSkip"] is False
    coal_before = g.state.plant_counts["coal"]
    assert g.slot_attached is None and g.state.plant_counts["coal"] == coal_before  # nothing replaced until confirmed
    window.ConfirmDialog.confirm()
    assert g.slot_attached == 1


def test_overwriting_a_slot_and_clearing_one_are_never_skippable(game_env):
    _storage()
    g = game_env.module
    _build_some(game_env)
    _select(game_env, 0)
    _click(game_env, "save")
    g.slot_attached = None
    window = _install_fake_confirm_dialog()
    _click(game_env, "save")
    assert window.ConfirmDialog.calls[-1]["id"] == "grid-slot-save" and window.ConfirmDialog.calls[-1]["allowSkip"] is False
    window.ConfirmDialog.confirm()
    assert g.slot_attached == 0
    _click(game_env, "new")
    assert window.ConfirmDialog.calls[-1]["id"] == "grid-slot-new" and window.ConfirmDialog.calls[-1]["allowSkip"] is False
    window.ConfirmDialog._pending_confirm = None
    _click(game_env, "clear")
    assert window.ConfirmDialog.calls[-1]["id"] == "grid-slot-clear" and window.ConfirmDialog.calls[-1]["allowSkip"] is False
    assert g.load_slots()[0] is not None  # not cleared until confirmed
    window.ConfirmDialog.confirm()
    assert g.load_slots()[0] is None and g.slot_attached is None
    assert g.state.plant_counts["coal"] == 2  # the run on screen is untouched by clearing


def test_reloading_the_attached_slot_only_asks_when_it_would_undo_something(game_env):
    _storage()
    g = game_env.module
    _build_some(game_env)
    _click(game_env, "save")
    window = _install_fake_confirm_dialog()
    _click(game_env, "load")          # identical to the saved run: no question
    assert window.ConfirmDialog.calls == [] and "Loaded slot 1" in g.slot_message
    game_env.build("coal")            # a change made since the last save
    _click(game_env, "load")
    assert window.ConfirmDialog.calls[-1]["id"] == "grid-slot-reload"
    assert g.state.plant_counts["coal"] == 3
    window.ConfirmDialog.confirm()
    assert g.state.plant_counts["coal"] == 2


def test_names_are_cleaned_and_capped(game_env):
    _storage()
    g = game_env.module
    assert g._clean_slot_name("  a   b  ", 0) == "a b"
    assert g._clean_slot_name("", 1) == "Slot 2"
    assert g._clean_slot_name(None, 2) == "Slot 3"
    assert len(g._clean_slot_name("x" * 100, 0)) == g.SLOT_NAME_MAX


def test_damaged_storage_means_empty_slots_never_a_crash(game_env):
    storage = _storage()
    g = game_env.module
    for junk in ("not json", "[]", '{"slots": "no"}', '{"slots": [1, null, {"state": 5}]}',
                 json.dumps({"slots": [{"name": "x", "state": {"round_number": "7"}}]}),
                 json.dumps({"slots": [{"name": "x", "state": {"round_number": True}}]})):
        storage.data[g.SLOTS_STORAGE_KEY] = junk
        assert g.load_slots() == [None, None, None]
    g.render()
    assert game_env.elements["slot-select"].innerHTML.count("empty") == 3


def test_a_hand_edited_slot_with_junk_numbers_is_treated_as_damaged(game_env):
    storage = _storage()
    g = game_env.module
    for state in ({"round_number": 4, "funds": "lots"}, {"round_number": 4, "plant_counts": {"coal": "many"}},
                  {"round_number": 4, "plant_counts": {"coal": -3}}, {"round_number": 4, "plant_counts": []},
                  {"round_number": 4, "demand": float("nan")}):
        storage.data[g.SLOTS_STORAGE_KEY] = json.dumps({"slots": [{"name": "<b>x</b>" * 10, "state": state}, None, None]})
        assert g.load_slots()[0] is None
    storage.data[g.SLOTS_STORAGE_KEY] = json.dumps({"slots": [{"name": "<b>x</b>" * 10, "state": {"round_number": 4}}, None, None]})
    assert len(g.load_slots()[0]["name"]) <= g.SLOT_NAME_MAX


def test_a_slot_that_blows_up_midway_leaves_the_run_on_screen_as_it_was(game_env):
    _storage()
    g = game_env.module
    _build_some(game_env, 2)
    _select(game_env, 0)
    _click(game_env, "save")
    _select(game_env, 1)
    _click(game_env, "new")
    game_env.build("solar")
    before = json.dumps(g.get_state(), sort_keys=True)
    real_render = g.render
    calls = {"n": 0}

    def exploding_render():
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("boom")
        real_render()

    g.render = exploding_render
    _select(game_env, 0)
    g.slot_switch_to(0)
    g.render = real_render
    assert "could not be read" in g.slot_message
    assert json.dumps(g.get_state(), sort_keys=True) == before
    assert g.slot_attached == 1


def test_a_full_browser_storage_never_breaks_play(game_env):
    storage = _storage()
    g = game_env.module

    def refuse(key, value):
        raise RuntimeError("quota")

    storage.setItem = refuse
    _build_some(game_env)
    assert g.slot_save_here(0) is False
    assert "would not store" in g.slot_message and g.slot_attached is None
    game_env.advance_round()
    assert g.state.round_number == 2


def test_a_run_that_is_too_large_is_refused(game_env):
    _storage()
    g = game_env.module
    g.state.event_log = [{"padding": "x" * 1000}] * 700
    assert g.slot_save_here(0) is False
    assert "too large" in g.slot_message


def test_slots_are_closed_to_the_sandbox_and_leave_the_real_game_alone(game_env):
    _storage()
    g = game_env.module
    _build_some(game_env)
    _click(game_env, "save")
    before = json.dumps(g.get_state(), sort_keys=True)
    g.sandbox_enter()
    assert g.slot_save_here(1) is False and "sandbox" in g.slot_message
    assert g.slot_switch_to(0) is False
    assert g.slot_new_run(1) is False
    game_env.advance_round()  # autosave must not write the sandbox grid into the attached slot
    assert g.load_slots()[0]["state"]["round_number"] == 1
    g.sandbox_leave()
    assert json.dumps(g.get_state(), sort_keys=True) == before


def test_slots_are_not_part_of_a_save(game_env):
    _storage()
    g = game_env.module
    _build_some(game_env)
    _click(game_env, "save")
    assert not any("slot" in key for key in g.get_state())


def test_the_desktop_page_offers_the_slots_in_the_menu():
    import pathlib
    config = json.loads((pathlib.Path(__file__).resolve().parent.parent / "pc-config.json").read_text())
    assert any(c["id"] == "pc-slots-panel" and "#slots-panel" in c["members"] for c in config["composites"])
