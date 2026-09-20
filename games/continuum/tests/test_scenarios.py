"""K12/K18 (planning/TODO.md) — starting scenarios and the hard-mode flag.

K12: "let the player pick a starting scenario or difficulty variant that
meaningfully changes initial conditions or challenge level" — before/at
game start, the same "toggle set, not a full menu system" UI shape Grid's
own difficulty toggles established (see games/grid/CLAUDE.md).

K18: "an optional stricter 'hard mode' sustainability variant" — covered
mostly in test_sustainability.py (the actual penalty/threshold tightening);
this file covers the flag's own plumbing (CityState default, save
round-trip, scenario/hard_mode validation).
"""

import sim
import save


def test_default_scenario_is_standard_and_matches_the_old_hardcoded_numbers():
    """A plain CityState() (no scenario argument) must produce byte-identical
    starting numbers to before K12 existed — every pre-existing test in
    tests/test_core_loop.py already depends on this implicitly."""
    state = sim.CityState()
    assert state.scenario == "standard"
    assert state.hard_mode is False
    assert state.population == sim.START_POPULATION
    assert state.resources["food"] == sim.START_FOOD
    assert state.resources["materials"] == sim.START_MATERIALS
    assert state.resources["tools"] == sim.START_TOOLS
    assert state.land_health == 1.0


def test_every_scenario_has_a_label_and_blurb():
    for scenario_id, config in sim.SCENARIOS.items():
        assert config["label"]
        assert config["blurb"]
        assert scenario_id  # non-empty key


def test_frontier_scenario_meaningfully_lowers_starting_conditions():
    standard = sim.CityState(scenario="standard")
    frontier = sim.CityState(scenario="frontier")
    assert frontier.scenario == "frontier"
    assert frontier.population < standard.population
    assert frontier.resources["food"] < standard.resources["food"]
    assert frontier.resources["materials"] < standard.resources["materials"]
    assert frontier.resources["tools"] < standard.resources["tools"]
    assert frontier.land_health < standard.land_health


def test_fertile_scenario_meaningfully_raises_starting_conditions():
    standard = sim.CityState(scenario="standard")
    fertile = sim.CityState(scenario="fertile")
    assert fertile.scenario == "fertile"
    assert fertile.population > standard.population
    assert fertile.resources["food"] > standard.resources["food"]
    assert fertile.resources["materials"] > standard.resources["materials"]
    assert fertile.resources["tools"] > standard.resources["tools"]


def test_every_scenario_starts_with_no_idle_worker_deficit():
    """START_ALLOCATION always assigns 5 workers -- every scenario's
    starting population must be at least that many, or a fresh settlement
    would start over-assigned (idle_workers() negative)."""
    for scenario_id in sim.SCENARIOS:
        state = sim.CityState(scenario=scenario_id)
        assert state.population >= state.assigned_workers()


def test_unrecognised_scenario_id_falls_back_to_standard():
    state = sim.CityState(scenario="not-a-real-scenario")
    assert state.scenario == "standard"
    assert state.population == sim.START_POPULATION


def test_scenario_config_falls_back_for_none():
    assert sim.scenario_config(None) == sim.SCENARIOS["standard"]


# --- save round-trip ------------------------------------------------------


def test_scenario_and_hard_mode_survive_a_save_round_trip():
    state = sim.CityState(scenario="fertile")
    state.hard_mode = True
    data = save.city_snapshot(state)

    fresh = sim.CityState()
    save.restore_city(fresh, data)
    assert fresh.scenario == "fertile"
    assert fresh.hard_mode is True


def test_restore_city_ignores_an_invalid_scenario_value():
    fresh = sim.CityState(scenario="frontier")
    save.restore_city(fresh, {"scenario": "not-a-real-scenario"})
    assert fresh.scenario == "frontier"  # kept, not overwritten with garbage


def test_restore_city_ignores_a_non_boolean_hard_mode_value():
    fresh = sim.CityState()
    fresh.hard_mode = True
    save.restore_city(fresh, {"hard_mode": "yes please"})
    assert fresh.hard_mode is True  # kept, not coerced from a truthy string


# --- game.py UI wiring: scenario select + hard-mode toggle ---------------


def test_scenario_buttons_start_unlocked_with_standard_selected(game_env):
    for scenario_id in sim.SCENARIOS:
        button = game_env.elements[f"scenario-{scenario_id}-button"]
        assert button.disabled is False
        assert button.classList.contains("selected") == (scenario_id == "standard")


def test_clicking_a_scenario_button_applies_its_starting_numbers(game_env):
    game_env.elements["scenario-frontier-button"].dispatch("click", None)
    state = game_env.state
    assert state.scenario == "frontier"
    assert state.population == sim.SCENARIOS["frontier"]["population"]
    assert state.resources["food"] == sim.SCENARIOS["frontier"]["food"]
    assert game_env.elements["scenario-frontier-button"].classList.contains("selected")
    assert not game_env.elements["scenario-standard-button"].classList.contains("selected")


def test_scenario_select_locks_after_the_first_season_advance(game_env):
    game_env.advance_season()
    for scenario_id in sim.SCENARIOS:
        assert game_env.elements[f"scenario-{scenario_id}-button"].disabled is True


def test_clicking_a_scenario_button_after_lock_does_nothing(game_env):
    game_env.advance_season()
    population_before = game_env.state.population
    game_env.elements["scenario-fertile-button"].dispatch("click", None)
    assert game_env.state.scenario == "standard"  # unchanged
    assert game_env.state.population == population_before


def test_clicking_an_unknown_scenario_id_is_a_safe_no_op(game_env):
    """Defensive: _make_select_scenario_handler() is only ever wired up
    for real sim.SCENARIOS keys, but the guard itself is cheap to pin down
    directly rather than trusting that wiring never drifts."""
    module = game_env.module
    handler = module._make_select_scenario_handler("not-a-real-scenario")
    handler()
    assert module.state.scenario == "standard"


def test_hard_mode_toggle_button_reflects_state_and_flips_on_click(game_env):
    button = game_env.elements["hard-mode-toggle-button"]
    assert "OFF" in button.innerText
    assert game_env.state.hard_mode is False

    button.dispatch("click", None)
    assert game_env.state.hard_mode is True
    assert "ON" in button.innerText
    assert button.classList.contains("active")

    button.dispatch("click", None)
    assert game_env.state.hard_mode is False
    assert "OFF" in button.innerText
    assert not button.classList.contains("active")


def test_hard_mode_can_be_toggled_after_the_scenario_lock(game_env):
    """Unlike scenario select, hard mode has no lock -- it can be flipped
    at any point in the playthrough, the same "toggle anytime" shape
    Grid's own difficulty toggles use."""
    game_env.advance_season()
    game_env.elements["hard-mode-toggle-button"].dispatch("click", None)
    assert game_env.state.hard_mode is True


def test_restore_city_tolerates_a_save_written_before_k12_k18_existed():
    """A save with no "scenario"/"hard_mode" keys at all (every save written
    before this session) must load without error and keep the live
    defaults — the same "missing means unchanged" standard restore_city()
    already holds every other field to."""
    fresh = sim.CityState()
    save.restore_city(fresh, {"population": 20})
    assert fresh.scenario == "standard"
    assert fresh.hard_mode is False
    assert fresh.population == 20


# --- through the real get_state()/load_state() widget contract -----------


def test_scenario_and_hard_mode_round_trip_through_the_real_save_widget_contract(game_env):
    """Not just save.restore_city() directly -- the actual
    get_state()/load_state() pair shared/save-widget.js drives every game
    through."""
    game_env.elements["scenario-fertile-button"].dispatch("click", None)
    game_env.elements["hard-mode-toggle-button"].dispatch("click", None)
    snapshot = game_env.module.get_state()
    assert snapshot["current_state"]["city"]["scenario"] == "fertile"
    assert snapshot["current_state"]["city"]["hard_mode"] is True

    # Diverge, then load the snapshot back.
    game_env.elements["scenario-standard-button"].dispatch("click", None)  # locked, no-op
    game_env.advance_season()
    game_env.elements["hard-mode-toggle-button"].dispatch("click", None)
    assert game_env.state.hard_mode is False

    assert game_env.module.load_state(snapshot) is True
    assert game_env.state.scenario == "fertile"
    assert game_env.state.hard_mode is True


def test_load_state_ignores_a_tampered_scenario_in_a_widget_save(game_env):
    snapshot = game_env.module.get_state()
    snapshot["current_state"]["city"]["scenario"] = "not-a-real-scenario"
    snapshot["current_state"]["city"]["hard_mode"] = "yes"  # not a real bool either
    assert game_env.module.load_state(snapshot) is True
    assert game_env.state.scenario == "standard"
    assert game_env.state.hard_mode is False
