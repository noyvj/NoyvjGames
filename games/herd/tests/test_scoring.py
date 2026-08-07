"""Milestone 5: scoring + hope-angle payoff. The core claim under test:
decoupled growth beats BOTH pure growth and pure restraint — proving
decoupling is better management, not a tax on growth.
"""


def test_score_starts_at_initial_funds(game_env):
    assert game_env.farm.score() == 300.0


def test_score_penalized_by_methane(game_env):
    game_env.farm.methane = 100.0
    assert game_env.farm.score() == 300.0 - 100 * 2.0


def _play_rounds(farm, rounds, grow_each_round=0, decouple_each_round=None):
    for _ in range(rounds):
        for _ in range(grow_each_round):
            farm.grow_herd()
        if decouple_each_round:
            for measure in decouple_each_round:
                farm.invest_decoupling(measure)
        farm.advance_round()
    return farm


def test_pure_restraint_scores_at_or_near_starting_funds(game_env):
    farm = game_env.module.FarmState()
    _play_rounds(farm, rounds=15)  # never grows the herd at all
    assert farm.score() == 300.0  # no income, no methane, nothing changes


def test_pure_growth_scores_lower_than_decoupled_growth(game_env):
    pure_growth = game_env.module.FarmState()
    for _ in range(6):
        pure_growth.grow_herd()
    _play_rounds(pure_growth, rounds=15)

    decoupled_growth = game_env.module.FarmState()
    for _ in range(6):
        decoupled_growth.grow_herd()
    for _ in range(5):
        decoupled_growth.invest_decoupling("capture")
    _play_rounds(decoupled_growth, rounds=15)

    assert decoupled_growth.score() > pure_growth.score()


def test_decoupled_growth_beats_pure_restraint_too(game_env):
    decoupled_growth = game_env.module.FarmState()
    for _ in range(6):
        decoupled_growth.grow_herd()
    for _ in range(5):
        decoupled_growth.invest_decoupling("capture")
    _play_rounds(decoupled_growth, rounds=15)

    restraint = game_env.module.FarmState()
    _play_rounds(restraint, rounds=15)

    assert decoupled_growth.score() > restraint.score()


def test_decoupled_growth_has_lower_methane_than_pure_growth_at_same_herd_size(game_env):
    pure_growth = game_env.module.FarmState()
    for _ in range(6):
        pure_growth.grow_herd()
    _play_rounds(pure_growth, rounds=15)

    decoupled_growth = game_env.module.FarmState()
    for _ in range(6):
        decoupled_growth.grow_herd()
    for _ in range(5):
        decoupled_growth.invest_decoupling("capture")
    _play_rounds(decoupled_growth, rounds=15)

    assert decoupled_growth.herd_size == pure_growth.herd_size == 6
    assert decoupled_growth.methane < pure_growth.methane


def test_render_shows_score(game_env):
    game_env.farm.methane = 100.0
    game_env.module.render()
    assert "100" in game_env.elements["score-display"].innerText
