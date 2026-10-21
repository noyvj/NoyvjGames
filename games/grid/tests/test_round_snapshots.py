from grid_rules import PLANT_TYPES
from grid_state import GridState


def test_fresh_state_has_empty_snapshots():
    state = GridState()
    assert state.round_snapshots == []


def test_single_round_snapshot(game_env):
    game_env.state.build_plant("coal")
    game_env.state.advance_round(rng=lambda: 1.0, age_rng=lambda: 1.0)
    snaps = game_env.state.round_snapshots
    assert len(snaps) == 1
    snap = snaps[0]
    assert snap["round"] == 1
    assert snap["demand"] == 100
    assert snap["plants"]["coal"] == 1
    assert set(snap["plants"].keys()) == set(PLANT_TYPES)
    assert snap["disruption"] is None
    assert snap["aging_plant"] is None
    assert snap["weather_pct"] is None


def test_snapshot_limit(game_env):
    for _ in range(105):
        game_env.state.advance_round(rng=lambda: 1.0, age_rng=lambda: 1.0)
    snaps = game_env.state.round_snapshots
    assert len(snaps) == 100
    assert snaps[-1]["round"] == 105


def test_save_load_round_snapshots(game_env):
    import copy
    game_env.state.build_plant("coal")
    game_env.state.advance_round(rng=lambda: 1.0, age_rng=lambda: 1.0)
    game_env.state.advance_round(rng=lambda: 1.0, age_rng=lambda: 1.0)

    data = game_env.module.get_state()
    assert "round_snapshots" in data
    assert len(data["round_snapshots"]) == 2

    # load twice gives same result
    game_env.module.load_state(copy.deepcopy(data))
    assert len(game_env.state.round_snapshots) == 2
    game_env.module.load_state(copy.deepcopy(data))
    assert len(game_env.state.round_snapshots) == 2


def test_fresh_save_no_round_snapshots_key(game_env):
    data = game_env.module.get_state()
    assert "round_snapshots" not in data


def test_load_clears_planted_fake_snapshots(game_env):
    game_env.state.round_snapshots.append({"round": 1, "demand": 0, "funds": 0, "plants": {t: 0 for t in PLANT_TYPES}, "disruption": None, "aging_plant": None, "weather_pct": None})
    data = {"round_snapshots": []}
    game_env.module.load_state(data)
    assert game_env.state.round_snapshots == []


def test_load_keeps_only_valid_snapshots(game_env):
    valid_snap = {
        "round": 1, "demand": 100.0, "funds": 500.0,
        "plants": {t: 1 for t in PLANT_TYPES},
        "disruption": "brownout", "aging_plant": "coal", "weather_pct": 10.0
    }
    data = {"round_snapshots": ["x", {"round": "a"}, valid_snap]}
    game_env.module.load_state(data)
    assert len(game_env.state.round_snapshots) == 1
    assert game_env.state.round_snapshots[0] == valid_snap


def test_scrub_lines_basic(game_env):
    snap = {
        "round": 2, "demand": 110, "funds": 420.0,
        "plants": {t: (1 if t == "coal" else 0) for t in PLANT_TYPES},
        "disruption": None, "aging_plant": None, "weather_pct": None
    }
    res = game_env.module.scrub_lines(snap)
    assert res == "Round 2: demand 110, funds after the round 420. Fleet after the round: Coal 1. Disruption: none. Weather: no variability this round."


def test_scrub_lines_disruption_aging(game_env):
    snap = {
        "round": 5, "demand": 150, "funds": 300.0,
        "plants": {t: 0 for t in PLANT_TYPES},
        "disruption": "damage", "aging_plant": "gas", "weather_pct": None
    }
    res = game_env.module.scrub_lines(snap)
    assert "Disruption: damage, aging breakdown of Gas" in res


def test_scrub_lines_weather(game_env):
    snap = {
        "round": 3, "demand": 120, "funds": 400.0,
        "plants": {t: 0 for t in PLANT_TYPES},
        "disruption": None, "aging_plant": None, "weather_pct": -12.4
    }
    res = game_env.module.scrub_lines(snap)
    assert "renewable output 12% below nameplate" in res


def test_scrub_lines_empty_fleet(game_env):
    snap = {
        "round": 1, "demand": 100, "funds": 500.0,
        "plants": {t: 0 for t in PLANT_TYPES},
        "disruption": None, "aging_plant": None, "weather_pct": None
    }
    res = game_env.module.scrub_lines(snap)
    assert "Fleet after the round: no plants" in res
