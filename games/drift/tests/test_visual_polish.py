"""Milestone 7: visual pass — strain-level colour coding on the strain
meter, so a glance at the bar's colour (not just its width) tells the
player whether the region is stable, strained, or critical.
"""


def test_strain_bar_class_stable_by_default(game_env):
    game_env.module.render()
    assert "strain--stable" in game_env.elements["strain-bar"].className


def test_strain_bar_class_critical_with_zero_capacity(game_env):
    game_env.advance_round()
    game_env.module.render()
    assert "strain--critical" in game_env.elements["strain-bar"].className


def test_strain_bar_class_strained_at_partial_shortfall(game_env):
    game_env.region.invest("housing")  # +10 capacity
    game_env.advance_round()
    game_env.advance_round()
    game_env.advance_round()  # total_arrivals=19.5, capacity=10 -> ~49% strain
    game_env.module.render()
    assert "strain--strained" in game_env.elements["strain-bar"].className
