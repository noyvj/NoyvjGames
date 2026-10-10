"""FY-53: the three-goals queue SOL hands to shared/goals-panel.js."""

import json
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent


def _goal(m, goal_id):
    return next((g for g in m.goals_list() if g["id"] == goal_id), None)


def test_fresh_game_queue_starts_with_the_cheap_steps(game_env):
    m = game_env.module
    ids = [g["id"] for g in m.goals_list()]
    assert ids[:3] == ["first_miner", "first_recycler", "research_near"]
    assert all(g["label"] and g["target"] >= 1 for g in m.goals_list())
    assert len(set(ids)) == len(ids)


def test_goals_json_round_trips(game_env):
    m = game_env.module
    assert json.loads(m.goals_json()) == m.goals_list()


def test_goals_follow_the_state(game_env):
    m = game_env.module
    assert _goal(m, "first_miner")["current"] == 0
    game_env.earth["resource_count"] = 1000
    game_env.buy_generator()
    assert _goal(m, "first_miner")["current"] == 1
    game_env.buy_recycler()
    assert _goal(m, "first_recycler")["current"] == 1
    game_env.earth["terraform_progress"] = 42.9
    assert _goal(m, "terraform_earth")["current"] == 42


def test_current_never_exceeds_target(game_env):
    m = game_env.module
    game_env.earth["resource_count"] = 10 ** 6
    for _ in range(5):
        game_env.buy_generator()
        game_env.buy_recycler()
    for goal in m.goals_list():
        assert 0 <= goal["current"] <= goal["target"]


def test_locked_worlds_have_no_terraform_goal_until_unlocked(game_env):
    m = game_env.module
    assert _goal(m, "terraform_mars") is None
    game_env.unlock_tier(1)
    assert _goal(m, "terraform_mars") is not None
    assert _goal(m, "terraform_moon") is not None
    assert _goal(m, "terraform_pluto") is None


def test_sky_city_goals_only_for_available_gas_giants(game_env):
    m = game_env.module
    assert _goal(m, "sky_jupitermoons") is None
    game_env.unlock_tier(2)
    assert _goal(m, "sky_jupitermoons") is not None
    assert _goal(m, "sky_saturnmoons") is not None


def test_visit_goals_use_visited_bodies(game_env):
    m = game_env.module
    assert _goal(m, "visit_mars")["current"] == 0
    m.visited_bodies.add("Mars")
    assert _goal(m, "visit_mars")["current"] == 1


def test_tick_refresh_is_a_no_op_without_the_shared_script(game_env):
    m = game_env.module
    for _ in range(25):
        m.tick()  # the fake js module has no NoyvjGoals; must not raise


def test_page_wiring():
    html = (GAME_DIR / "index.html").read_text()
    assert 'id="goals"' in html
    assert "shared/goals-panel.js" in html  # the script links its own stylesheet
    assert 'id="goals-checkbox"' in html
    assert '"#goals"' in (GAME_DIR / "pc-config.json").read_text()
