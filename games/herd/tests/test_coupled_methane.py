"""Milestone 2: the coupled methane meter — rises automatically and
proportionally to herd size, no separate player choice required.
"""


def test_methane_starts_at_zero(game_env):
    assert game_env.farm.methane == 0.0


def test_coupling_ratio_starts_at_base_value(game_env):
    assert game_env.farm.coupling_ratio() == 1.0


def test_methane_this_round_scales_with_herd_size(game_env):
    game_env.grow_herd()
    game_env.grow_herd()
    game_env.grow_herd()
    assert game_env.farm.methane_this_round() == 3.0


def test_advance_round_accumulates_methane(game_env):
    game_env.grow_herd()
    game_env.grow_herd()
    game_env.advance_round()
    assert game_env.farm.methane == 2.0


def test_methane_accumulates_across_multiple_rounds(game_env):
    game_env.grow_herd()
    game_env.advance_round()
    game_env.grow_herd()
    game_env.advance_round()
    # round 1: herd=1, +1 methane. round 2: herd=2, +2 methane. total=3
    assert game_env.farm.methane == 3.0


def test_no_herd_means_no_methane(game_env):
    game_env.advance_round()
    game_env.advance_round()
    assert game_env.farm.methane == 0.0


def test_methane_is_a_direct_consequence_not_a_separate_choice(game_env):
    # The coupling is automatic: growing the herd is the only action taken,
    # yet methane rises as an unavoidable side effect.
    funds_before = game_env.farm.funds
    game_env.grow_herd()
    game_env.advance_round()
    assert game_env.farm.methane > 0
    assert game_env.farm.funds != funds_before  # herd growth had a cost too


def test_render_shows_methane_and_coupling_ratio(game_env):
    game_env.grow_herd()
    game_env.advance_round()
    assert "1" in game_env.elements["methane-display"].innerText
    assert "1.00" in game_env.elements["coupling-display"].innerText
