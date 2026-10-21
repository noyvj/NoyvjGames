from grid_state import GridState


def test_capacity_history_fresh():
    state = GridState()
    assert state.capacity_history == []


def test_capacity_history_after_builds_and_advances():
    state = GridState()
    state.build_plant("coal")
    state.advance_round(rng=lambda: 1.0, age_rng=lambda: 1.0)
    state.build_plant("nuclear")
    state.advance_round(rng=lambda: 1.0, age_rng=lambda: 1.0)
    assert state.capacity_history == [20, 120]
