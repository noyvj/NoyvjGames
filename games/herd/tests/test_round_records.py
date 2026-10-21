import herd_model as m


def test_fresh_farm_round_records(game_env):
    """A fresh farm starts with one round record: [0, BASE_COUPLING_RATIO, 0.0]."""
    assert game_env.farm.round_records == [[0, game_env.module.BASE_COUPLING_RATIO, 0.0]]


def test_round_records_after_growth_and_advance(game_env):
    """Growing the herd twice and advancing a round appends a record matching current state."""
    game_env.grow_herd()
    game_env.grow_herd()
    game_env.advance_round()

    farm = game_env.farm
    assert len(farm.round_records) == len(farm.methane_history) == 2
    assert farm.round_records[1][0] == 2
    assert farm.round_records[1][1] == farm.coupling_ratio()
    assert farm.round_records[1][2] == farm.pressure_fraction()


def test_clone_farm_copies_round_records(game_env):
    """clone_farm copies round_records into a new list, not the same object."""
    game_env.grow_herd()
    game_env.advance_round()

    original = game_env.farm.round_records
    twin = m.clone_farm(game_env.farm)
    assert twin.round_records == original
    assert twin.round_records is not original
