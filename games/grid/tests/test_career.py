"""C1: grid operator career -- persistent cross-run points and perks."""
import json
import sys


class FakeStorage:
    def __init__(self, initial=None):
        self.data = dict(initial or {})

    def getItem(self, key):
        return self.data.get(key)

    def setItem(self, key, value):
        self.data[key] = value


def _install_storage(initial=None):
    storage = FakeStorage(initial)
    sys.modules["js"].localStorage = storage
    return storage


def _play(game_env, rounds):
    for _ in range(rounds):
        game_env.state.advance_round(rng=lambda: 1.0, age_rng=lambda: 1.0)


def test_short_run_banks_nothing(game_env):
    g = game_env.module
    _play(game_env, 2)
    assert g.finish_run() is None
    assert g.career["runs"] == 0
    game_env.toggle_career()
    assert game_env.elements["career-finish-button"].disabled is True
    assert "at least" in game_env.elements["career-preview-display"].innerText


def test_finish_run_banks_points_and_resets_grid(game_env):
    g = game_env.module
    storage = _install_storage()
    game_env.state.plant_counts["solar"] = 5
    _play(game_env, 6)
    points, _ = g.run_career_points()
    assert points >= 1
    assert g.finish_run() == points
    assert g.career["runs"] == 1 and g.career["points"] == points
    assert game_env.state.round_number == 1  # fresh grid
    assert sum(game_env.state.plant_counts.values()) == 0
    assert json.loads(storage.data[g.CAREER_STORAGE_KEY])["runs"] == 1


def test_unlock_requires_points_and_deducts(game_env):
    g = game_env.module
    _install_storage()
    assert g.unlock_career_perk("seed_capital") is False
    g.career["points"] = 4
    assert g.unlock_career_perk("seed_capital") is True
    assert g.career_points_available() == 1
    assert g.unlock_career_perk("seed_capital") is False  # already owned
    assert g.unlock_career_perk("crew_training") is False  # cannot afford
    assert g.unlock_career_perk("nope") is False


def test_seed_capital_applies_to_next_run(game_env):
    g = game_env.module
    _install_storage()
    g.career["points"] = 10
    g.unlock_career_perk("seed_capital")
    _play(game_env, 6)
    g.finish_run()
    assert game_env.state.funds == g.STARTING_FUNDS + g.SEED_CAPITAL_BONUS


def test_perks_change_costs(game_env):
    g = game_env.module
    state = game_env.state
    base_m = state.maintenance_cost("coal")
    base_d = state.demand_response_cost()
    base_e = state.arbitrage_efficiency()
    state.perks = {"crew_training", "demand_analytics", "storage_partners"}
    assert state.maintenance_cost("coal") < base_m
    assert state.demand_response_cost() < base_d
    assert state.arbitrage_efficiency() > base_e == g.ARBITRAGE_EFFICIENCY


def test_perks_do_not_touch_emissions_or_disruption(game_env):
    state = game_env.state
    state.plant_counts["coal"] = 3
    before = (state.emissions_this_round(), state.disruption_probability(), state.plant_cost("solar"))
    state.perks = {"crew_training", "demand_analytics", "storage_partners", "seed_capital"}
    assert before == (state.emissions_this_round(), state.disruption_probability(), state.plant_cost("solar"))


def test_load_career_from_storage_valid_and_corrupt(game_env):
    g = game_env.module
    _install_storage({g.CAREER_STORAGE_KEY: json.dumps({"runs": 3, "points": 7, "unlocked": ["seed_capital"]})})
    c = g.load_career_from_storage()
    assert c["runs"] == 3 and c["unlocked"] == ["seed_capital"]
    _install_storage({g.CAREER_STORAGE_KEY: "{not json"})
    assert g.load_career_from_storage() == g._default_career()


def test_validate_career_defaults_and_clamps(game_env):
    g = game_env.module
    assert g.validate_career("junk") == g._default_career()
    c = g.validate_career(
        {"runs": -5, "points": "many", "best_score": 900, "best_grade": "Z",
         "unlocked": ["seed_capital", "bogus"], "achievements": [1, "x"]}
    )
    assert c["runs"] == 0 and c["points"] == 0 and c["best_score"] == 100.0
    assert c["best_grade"] is None
    assert c["unlocked"] == []  # cannot be afforded with 0 points
    assert c["achievements"] == ["x"]


def test_saved_career_never_rolls_back_live_progress(game_env):
    g = game_env.module
    _install_storage()
    g.career["runs"] = 5
    g.career["points"] = 9
    snap = g.get_state()
    stale = dict(snap)
    stale["career"] = {"runs": 1, "points": 1}
    g.load_state(stale)
    assert g.career["runs"] == 5
    newer = dict(snap)
    newer["career"] = {"runs": 8, "points": 20, "unlocked": ["crew_training"]}
    g.load_state(newer)
    assert g.career["runs"] == 8 and "crew_training" in game_env.state.perks


def test_banked_achievements_persist_across_runs(game_env):
    g = game_env.module
    _install_storage()
    game_env.state.plant_counts["solar"] = 1
    game_env.state.cumulative_built["solar"] = 1
    _play(game_env, 6)
    earned = set(g.achievement_ids_earned())
    g.finish_run()
    assert earned <= set(g.achievement_ids_earned())
    assert earned <= set(g.get_state()["achievements_earned"])


def test_career_panel_renders_and_unlock_button(game_env):
    g = game_env.module
    _install_storage()
    g.career["points"] = 3
    game_env.toggle_career()
    assert game_env.elements["career-panel"].hidden is False
    btn = game_env.elements["career-unlock-seed_capital-button"]
    assert btn.disabled is False and "3 pts" in btn.innerText
    assert game_env.elements["career-unlock-crew_training-button"].disabled is True
    btn.dispatch("click", None)
    assert "Unlocked" in btn.innerText and btn.disabled is True
    assert "0 to spend" in game_env.elements["career-stats-display"].innerText


def test_finish_button_via_ui(game_env):
    g = game_env.module
    _install_storage()
    _play(game_env, 6)
    game_env.toggle_career()
    game_env.elements["career-finish-button"].dispatch("click", None)  # no ConfirmDialog in fake -> immediate
    assert g.career["runs"] == 1
