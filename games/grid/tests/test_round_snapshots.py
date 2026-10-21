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
