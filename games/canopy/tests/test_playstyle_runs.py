"""B7 (planning/TODO.md "Per-game: Canopy"): save/compare two named
playstyle runs. Per-browser via localStorage, same mechanism as B14's
personal best -- deliberately independent of the save-code system and
NOT reset by reset_session()."""

import json


def test_playstyle_runs_start_empty(game_env):
    m = game_env.module
    assert m.playstyle_runs == {"a": None, "b": None}


def test_comparison_html_empty_before_any_run_saved(game_env):
    m = game_env.module
    assert m.playstyle_comparison_html() == ""


def test_saving_run_a_captures_current_stats(game_env):
    m = game_env.module
    game_env.tick(5)
    game_env.select(0)
    game_env.clear()

    game_env.save_playstyle_run_a()

    run_a = m.playstyle_runs["a"]
    assert run_a is not None
    assert run_a["income"] == m.total_income
    assert run_a["standing_value"] == m.standing_forest_value()
    assert run_a["biodiversity"] == m.total_biodiversity()
    assert run_a["plots_total"] == len(m.plots)
    assert run_a["grid_size"] == m.current_grid_size
    assert m.playstyle_runs["b"] is None


def test_saving_both_runs_populates_comparison_table(game_env):
    m = game_env.module
    game_env.tick(3)
    game_env.save_playstyle_run_a()
    game_env.tick(3)
    game_env.save_playstyle_run_b()

    html = m.playstyle_comparison_html()
    assert "<table" in html
    assert "Run A" in html
    assert "Run B" in html
    # Run B was saved later, after more ticks, so its standing value
    # should be strictly higher (nothing was ever cleared).
    assert m.playstyle_runs["b"]["standing_value"] > m.playstyle_runs["a"]["standing_value"]


def test_saved_runs_persist_to_local_storage(game_env):
    m = game_env.module
    game_env.tick(2)
    game_env.save_playstyle_run_a()

    stored = game_env.local_storage.getItem(m.PLAYSTYLE_RUNS_STORAGE_KEY)
    assert stored is not None
    data = json.loads(stored)
    assert data["a"]["income"] == m.playstyle_runs["a"]["income"]
    assert data["b"] is None


def test_load_playstyle_runs_reads_existing_storage(game_env):
    m = game_env.module
    game_env.local_storage.setItem(
        m.PLAYSTYLE_RUNS_STORAGE_KEY,
        json.dumps({"a": {"income": 42.0, "standing_value": 1.0, "biodiversity": 0.0,
                           "plots_standing": 1, "plots_total": 36, "grid_size": "normal"},
                    "b": None}),
    )
    loaded = m.load_playstyle_runs()
    assert loaded["a"]["income"] == 42.0
    assert loaded["b"] is None


def test_load_playstyle_runs_defaults_on_malformed_storage(game_env):
    m = game_env.module
    game_env.local_storage.setItem(m.PLAYSTYLE_RUNS_STORAGE_KEY, "not json")
    assert m.load_playstyle_runs() == {"a": None, "b": None}


def test_reset_session_does_not_clear_playstyle_runs(game_env):
    m = game_env.module
    game_env.tick(3)
    game_env.save_playstyle_run_a()
    game_env.reset_session()
    assert m.playstyle_runs["a"] is not None


def test_invalid_slot_is_a_noop(game_env):
    m = game_env.module
    result = m.save_playstyle_run("c")
    assert result is False
    assert m.playstyle_runs == {"a": None, "b": None}


def test_opening_summary_panel_renders_comparison_prompt_when_empty(game_env):
    game_env.toggle_session_summary()
    text = game_env.elements["session-summary-playstyle-comparison"].innerText
    assert "Save a run" in text


def test_saving_a_run_updates_the_open_panel(game_env):
    game_env.toggle_session_summary()
    game_env.tick(2)
    game_env.save_playstyle_run_a()
    html = game_env.elements["session-summary-playstyle-comparison"].innerHTML
    assert "<table" in html
