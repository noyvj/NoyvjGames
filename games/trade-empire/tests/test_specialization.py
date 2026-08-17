"""Milestone 10: colony specialization. Every colony has a fixed,
environmental strength/weakness pair (reflecting its own flavor text,
not a player choice) that activates automatically once it develops
(Milestone 9's development_level >= 2) -- distinct output bonuses and
decay penalties per colony, not a uniform bonus applied everywhere.
"""

import pytest


def test_every_colony_has_a_specialization(game_env):
    for colony_id in game_env.module.COLONIES:
        assert colony_id in game_env.module.SPECIALIZATION


def test_specializations_are_not_identical_across_colonies(game_env):
    bonuses = {spec["output_bonus"] for spec in game_env.module.SPECIALIZATION.values()}
    assert len(bonuses) > 1  # genuinely distinct, not one bonus copy-pasted five times


def test_specialization_inactive_before_development(game_env):
    state = game_env.module.colony_states["aurum"]
    unspecialized_multiplier = (
        game_env.module.MIN_OUTPUT_MULTIPLIER
        + state.need_satisfaction
        * (game_env.module.MAX_OUTPUT_MULTIPLIER - game_env.module.MIN_OUTPUT_MULTIPLIER)
    )
    assert state.output_multiplier() == pytest.approx(unspecialized_multiplier)


def test_specialization_output_bonus_applies_once_developed(game_env):
    state = game_env.module.colony_states["aurum"]
    pre_development_multiplier = state.output_multiplier()
    state.deliver(game_env.module.DEVELOPMENT_THRESHOLD)
    assert state.is_developed()
    # Same underlying satisfaction-based formula, scaled up by the
    # colony's own output bonus on top.
    bonus = game_env.module.SPECIALIZATION["aurum"]["output_bonus"]
    base = (
        game_env.module.MIN_OUTPUT_MULTIPLIER
        + ((state.need_satisfaction + state.secondary_need_satisfaction) / 2)
        * (game_env.module.MAX_OUTPUT_MULTIPLIER - game_env.module.MIN_OUTPUT_MULTIPLIER)
    )
    assert state.output_multiplier() == pytest.approx(base * (1 + bonus))
    assert state.output_multiplier() != pre_development_multiplier


def test_specialization_decay_penalty_inactive_before_development(game_env):
    state = game_env.module.colony_states["aurum"]
    satisfaction_before = state.need_satisfaction
    state.decay()
    assert state.need_satisfaction == pytest.approx(
        satisfaction_before - game_env.module.NEED_DECAY_PER_TICK
    )


def test_specialization_decay_penalty_applies_once_developed(game_env):
    state = game_env.module.colony_states["aurum"]
    state.deliver(game_env.module.DEVELOPMENT_THRESHOLD)
    satisfaction_before = state.need_satisfaction
    state.decay()
    expected_rate = game_env.module.NEED_DECAY_PER_TICK * game_env.module.SPECIALIZATION["aurum"]["decay_multiplier"]
    assert state.need_satisfaction == pytest.approx(max(0.0, satisfaction_before - expected_rate))


def test_different_colonies_have_different_decay_penalties(game_env):
    aurum_rate = game_env.module.SPECIALIZATION["aurum"]["decay_multiplier"]
    verdant_rate = game_env.module.SPECIALIZATION["verdant"]["decay_multiplier"]
    assert aurum_rate != verdant_rate


def test_render_shows_specialization_name_once_developed(game_env):
    game_env.module.colony_states["aurum"].deliver(game_env.module.DEVELOPMENT_THRESHOLD)
    game_env.module.render()
    text = game_env.elements["colony-aurum-development-display"].innerText
    assert "Mining Powerhouse" in text


def test_render_does_not_show_specialization_before_development(game_env):
    game_env.module.render()
    text = game_env.elements["colony-aurum-development-display"].innerText
    assert "Mining Powerhouse" not in text
