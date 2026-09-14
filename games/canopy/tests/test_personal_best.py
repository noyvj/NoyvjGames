"""B14 (planning/TODO.md "Per-game: Canopy"): a persisted, per-browser
"personal best" for standing value + income, via localStorage --
deliberately independent of the save-code system (get_state()/
load_state() never touch this)."""

import json


def test_personal_best_starts_at_zero_with_empty_storage(game_env):
    m = game_env.module
    assert m.personal_best == {"standing_value": 0.0, "income": 0.0}


def test_personal_best_display_starts_at_zero(game_env):
    text = game_env.elements["personal-best-display"].innerText
    assert "standing 0.0" in text
    assert "income 0.0" in text


def test_personal_best_updates_as_standing_value_rises(game_env):
    m = game_env.module
    game_env.tick(5)
    assert m.personal_best["standing_value"] == m.standing_forest_value()
    assert m.personal_best["standing_value"] > 0


def test_personal_best_updates_as_income_rises(game_env):
    m = game_env.module
    game_env.tick(3)  # let plot 0 accrue some value first
    game_env.select(0)
    game_env.clear()
    assert m.personal_best["income"] == m.total_income
    assert m.personal_best["income"] > 0


def test_personal_best_is_persisted_to_local_storage(game_env):
    m = game_env.module
    game_env.tick(3)
    game_env.select(0)
    game_env.clear()
    stored = game_env.local_storage.getItem(m.PERSONAL_BEST_STORAGE_KEY)
    assert stored is not None
    data = json.loads(stored)
    assert data["income"] == m.personal_best["income"]


def test_personal_best_never_decreases(game_env):
    m = game_env.module
    game_env.tick(10)
    best_after_growth = m.personal_best["standing_value"]
    game_env.select(0)
    game_env.clear()  # banks plot 0's value as income, plot 0's own value resets to 0
    # Total standing value across the *other* 35 plots is still growing,
    # so this isn't a great adversarial test on its own -- directly force
    # a drop in the live total to confirm the best doesn't follow it down.
    for plot in m.plots:
        plot.value = 0.0
    game_env.select(1)  # trigger a render without ticking
    assert m.personal_best["standing_value"] == best_after_growth


def test_personal_best_is_not_part_of_get_state(game_env):
    m = game_env.module
    assert "personal_best" not in m.get_state()


def test_load_personal_best_reads_existing_storage(game_env):
    m = game_env.module
    game_env.local_storage.setItem(
        m.PERSONAL_BEST_STORAGE_KEY, json.dumps({"standing_value": 500.0, "income": 250.0})
    )
    loaded = m.load_personal_best()
    assert loaded == {"standing_value": 500.0, "income": 250.0}


def test_load_personal_best_defaults_on_malformed_storage(game_env):
    m = game_env.module
    game_env.local_storage.setItem(m.PERSONAL_BEST_STORAGE_KEY, "not json")
    assert m.load_personal_best() == {"standing_value": 0.0, "income": 0.0}


def test_load_personal_best_defaults_on_missing_keys(game_env):
    m = game_env.module
    game_env.local_storage.setItem(m.PERSONAL_BEST_STORAGE_KEY, json.dumps({}))
    assert m.load_personal_best() == {"standing_value": 0.0, "income": 0.0}
