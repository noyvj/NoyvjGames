"""Round-7 pass: operator ranks and their cosmetic accent colours (C-17)."""
from .test_career import _install_storage


def _choose(game_env, value):
    el = game_env.elements["rank-theme-select"]
    el.value = value

    class _E:
        target = el

    el.dispatch("change", _E())


def _career(g, rounds, points):
    g.career["lifetime"]["rounds"] = rounds
    g.career["lifetime"]["scenario_grades"] = {"standard": {"n": 3, "points": points}}


def test_a_new_operator_is_a_junior_dispatcher(game_env):
    g = game_env.module
    g.render()
    assert g.operator_experience() == 0 and g.operator_rank_name() == "Junior Dispatcher"
    assert game_env.elements["rank-display"].innerText == "Rank: Junior Dispatcher"
    assert g.unlocked_rank_themes() == ("default",)


def test_experience_is_rounds_plus_weighted_grade_points(game_env):
    g = game_env.module
    _career(g, 20, 8)
    assert g.operator_experience() == 20 + 15 * 8


def test_rank_thresholds(game_env):
    g = game_env.module
    names = [g.operator_rank_name(xp) for xp in (0, 39, 40, 119, 120, 259, 260, 449, 450, 699, 700, 5000)]
    assert names == ["Junior Dispatcher", "Junior Dispatcher", "Dispatcher", "Dispatcher", "Senior Dispatcher",
                     "Senior Dispatcher", "Shift Supervisor", "Shift Supervisor", "Control Room Lead",
                     "Control Room Lead", "Chief Engineer", "Chief Engineer"]
    assert len(g.OPERATOR_RANKS) == len(g.RANK_THEMES) == 6


def test_rank_text_names_the_next_rank_and_the_gap(game_env):
    g = game_env.module
    _career(g, 10, 2)  # 40 xp: Dispatcher
    text = g.operator_rank_text()
    assert "Dispatcher (experience 40)" in text and "Next: Senior Dispatcher at 120 (80 to go)" in text
    assert "change no rule" in text
    _career(g, 1000, 40)
    assert "highest rank" in g.operator_rank_text()


def test_finishing_runs_raises_the_rank(game_env):
    g = game_env.module
    _install_storage()
    game_env.state.plant_counts["solar"] = 6
    for _ in range(12):
        game_env.state.advance_round(rng=lambda: 1.0, age_rng=lambda: 1.0)
    before = g.operator_experience()
    g.finish_run()
    assert g.operator_experience() > before


def test_locked_themes_are_refused_with_the_rank_needed(game_env):
    g = game_env.module
    _choose(game_env, "gold")
    assert g.prefs["rank_theme"] == "default"
    assert "unlocks at the rank Chief Engineer" in game_env.elements["rank-theme-note"].innerText
    assert game_env.elements["rank-theme-select"].value == "default"


def test_unlocked_theme_is_applied_to_header_and_panel(game_env):
    g = game_env.module
    _career(g, 130, 0)  # Senior Dispatcher: default, teal, amber
    g.render()
    _choose(game_env, "amber")
    assert g.prefs["rank_theme"] == "amber"
    assert game_env.elements["rank-display"].dataset.rankTheme == "amber"
    assert game_env.elements["career-panel"].dataset.rankTheme == "amber"
    assert "3 of 6 accent colours unlocked" in game_env.elements["rank-theme-note"].innerText


def test_a_stored_theme_falls_back_if_the_rank_is_not_there(game_env):
    g = game_env.module
    g.prefs["rank_theme"] = "rose"
    assert g.current_rank_theme() == "default"
    g.render()
    assert game_env.elements["rank-display"].dataset.rankTheme == "default"


def test_ranks_change_no_rule_and_are_not_saved(game_env):
    g = game_env.module
    before = g.get_state()
    _career(g, 900, 80)
    g.render()
    after = g.get_state()
    assert {k: v for k, v in after.items() if k != "career"} == {k: v for k, v in before.items() if k != "career"}
    assert not any("rank" in key for key in before)
    state_cost = game_env.state.plant_cost("coal")
    _career(g, 0, 0)
    assert game_env.state.plant_cost("coal") == state_cost
