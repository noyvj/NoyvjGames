"""Milestone 9: evolving needs v2. Sustained delivery of a colony's
primary need develops it further; development expands what it needs (a
second, cross-cycle need) rather than ever "solving" it -- there's no
final state, just an ongoing relationship between development and
demand.
"""

import pytest


def test_colonies_start_at_development_level_one(game_env):
    for colony_id in game_env.module.COLONIES:
        assert game_env.module.colony_states[colony_id].development_level == 1
        assert game_env.module.colony_states[colony_id].is_developed() is False


def test_delivering_below_threshold_does_not_develop(game_env):
    state = game_env.module.colony_states["aurum"]
    state.deliver(game_env.module.DEVELOPMENT_THRESHOLD - 10)
    assert state.development_level == 1


def test_delivering_past_threshold_develops_the_colony(game_env):
    state = game_env.module.colony_states["aurum"]
    state.deliver(game_env.module.DEVELOPMENT_THRESHOLD)
    assert state.development_level == 2
    assert state.is_developed() is True


def test_cumulative_delivered_accumulates_across_multiple_deliveries(game_env):
    state = game_env.module.colony_states["aurum"]
    for _ in range(5):
        state.deliver(10)
    assert state.cumulative_delivered == 50


def test_every_colony_has_a_secondary_need(game_env):
    for colony_id in game_env.module.COLONIES:
        assert colony_id in game_env.module.SECONDARY_NEED


def test_secondary_need_differs_from_primary_need(game_env):
    for colony_id, colony in game_env.module.COLONIES.items():
        assert game_env.module.SECONDARY_NEED[colony_id] != colony["needs"]


def test_secondary_need_reaches_into_the_other_cycle(game_env):
    # Aurum/Verdant/Ferrum are the original triangle; Cryo/Helion are
    # the pair. A developed triangle colony's secondary need should
    # come from the pair's goods, and vice versa -- that's the whole
    # point of "evolving needs create new cross-cluster dependencies."
    triangle_goods = {game_env.module.ORE, game_env.module.GRAIN, game_env.module.MACHINERY}
    pair_goods = {game_env.module.WATER, game_env.module.ENERGY}
    for colony_id in ("aurum", "verdant", "ferrum"):
        assert game_env.module.SECONDARY_NEED[colony_id] in pair_goods
    for colony_id in ("cryo", "helion"):
        assert game_env.module.SECONDARY_NEED[colony_id] in triangle_goods


def test_secondary_need_satisfaction_untouched_before_development(game_env):
    state = game_env.module.colony_states["aurum"]
    state.deliver_secondary(10)  # delivered anyway, shouldn't matter to output yet
    assert state.output_multiplier() == (
        game_env.module.MIN_OUTPUT_MULTIPLIER
        + state.need_satisfaction * (game_env.module.MAX_OUTPUT_MULTIPLIER - game_env.module.MIN_OUTPUT_MULTIPLIER)
    )


def test_output_multiplier_averages_both_needs_once_developed(game_env):
    state = game_env.module.colony_states["aurum"]
    state.deliver(game_env.module.DEVELOPMENT_THRESHOLD)  # develops it, satisfaction now high
    state.secondary_need_satisfaction = 0.0  # unmet secondary need
    avg = (state.need_satisfaction + 0.0) / 2
    base = game_env.module.MIN_OUTPUT_MULTIPLIER + avg * (
        game_env.module.MAX_OUTPUT_MULTIPLIER - game_env.module.MIN_OUTPUT_MULTIPLIER
    )
    # Milestone 10: developed colonies also carry their specialization's
    # output bonus on top of the needs-based base multiplier.
    expected = base * (1 + game_env.module.SPECIALIZATION["aurum"]["output_bonus"])
    assert state.output_multiplier() == pytest.approx(expected)


def test_decay_only_affects_secondary_need_once_developed(game_env):
    state = game_env.module.colony_states["aurum"]
    state.secondary_need_satisfaction = 0.5
    state.decay()
    assert state.secondary_need_satisfaction == 0.5  # untouched, not developed yet

    state.development_level = 2
    state.decay()
    assert state.secondary_need_satisfaction < 0.5


def test_delivering_secondary_good_to_developed_colony_raises_it(game_env):
    # Aurum's secondary need is energy (from Helion).
    aurum_state = game_env.module.colony_states["aurum"]
    aurum_state.development_level = 2
    aurum_state.secondary_need_satisfaction = 0.2

    ship = game_env.ship("4")
    ship.location = "helion"  # reposition directly to produce+deliver energy
    ship.load()
    ship.depart("aurum")
    game_env.tick(game_env.module.TRAVEL_TICKS)

    assert aurum_state.secondary_need_satisfaction > 0.2


def test_delivering_secondary_good_to_undeveloped_colony_does_not_raise_it(game_env):
    aurum_state = game_env.module.colony_states["aurum"]
    assert aurum_state.is_developed() is False
    before = aurum_state.secondary_need_satisfaction

    ship = game_env.ship("4")
    ship.location = "helion"
    ship.load()
    ship.depart("aurum")
    game_env.tick(game_env.module.TRAVEL_TICKS)

    assert aurum_state.secondary_need_satisfaction == before


def test_render_shows_development_level_one_progress(game_env):
    game_env.module.render()
    text = game_env.elements["colony-aurum-development-display"].innerText
    assert "Level 1" in text
    assert "0/" in text


def test_render_shows_development_level_two_once_developed(game_env):
    game_env.module.colony_states["aurum"].deliver(game_env.module.DEVELOPMENT_THRESHOLD)
    game_env.module.render()
    text = game_env.elements["colony-aurum-development-display"].innerText
    assert "Level 2" in text


def test_render_shows_secondary_need_once_developed(game_env):
    state = game_env.module.colony_states["aurum"]
    state.deliver(game_env.module.DEVELOPMENT_THRESHOLD)
    game_env.module.render()
    text = game_env.elements["colony-aurum-need-display"].innerText
    assert "also needs Energy" in text


def test_render_does_not_show_secondary_need_before_development(game_env):
    game_env.module.render()
    text = game_env.elements["colony-aurum-need-display"].innerText
    assert "also needs" not in text
