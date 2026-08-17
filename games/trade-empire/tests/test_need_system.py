"""Milestone 3: colony need system v1. Each colony's need_satisfaction
decays over time and is topped up when a ship delivers the colony's
needed good; output (cargo capacity) scales with it, so keeping the
loop fed is a real incentive, not just flavor text.
"""


def test_colonies_start_at_baseline_satisfaction(game_env):
    for colony_id in game_env.module.COLONIES:
        state = game_env.module.colony_states[colony_id]
        assert state.need_satisfaction == game_env.module.STARTING_NEED_SATISFACTION


def test_baseline_satisfaction_matches_milestone_1_2_cargo_capacity(game_env):
    # 0.5 satisfaction -> multiplier 1.0 -> unchanged CARGO_CAPACITY,
    # so this milestone doesn't shift the existing balance at baseline.
    state = game_env.module.colony_states["aurum"]
    assert state.cargo_capacity() == game_env.module.CARGO_CAPACITY


def test_need_satisfaction_decays_each_tick(game_env):
    game_env.tick(1)
    state = game_env.module.colony_states["aurum"]
    assert state.need_satisfaction < game_env.module.STARTING_NEED_SATISFACTION


def test_need_satisfaction_floors_at_zero(game_env):
    state = game_env.module.colony_states["aurum"]
    for _ in range(1000):
        state.decay()
    assert state.need_satisfaction == 0.0


def test_deliver_raises_satisfaction(game_env):
    state = game_env.module.colony_states["aurum"]
    before = state.need_satisfaction
    state.deliver(10)
    assert state.need_satisfaction > before


def test_deliver_caps_at_one(game_env):
    state = game_env.module.colony_states["aurum"]
    state.deliver(10000)
    assert state.need_satisfaction == 1.0


def test_output_multiplier_scales_with_satisfaction(game_env):
    state = game_env.module.colony_states["aurum"]
    state.need_satisfaction = 0.0
    low = state.output_multiplier()
    state.need_satisfaction = 1.0
    high = state.output_multiplier()
    assert low == game_env.module.MIN_OUTPUT_MULTIPLIER
    assert high == game_env.module.MAX_OUTPUT_MULTIPLIER
    assert high > low


def test_load_reads_cargo_qty_from_colony_output(game_env):
    state = game_env.module.colony_states["aurum"]
    state.need_satisfaction = 1.0  # max output
    game_env.load(ship_id="1")
    assert game_env.ship("1").cargo_qty == state.cargo_capacity()
    assert game_env.ship("1").cargo_qty > game_env.module.CARGO_CAPACITY


def test_delivering_the_needed_good_raises_destination_satisfaction(game_env):
    # Aurum needs grain; ship 2 starts at verdant (produces grain).
    verdant_state = game_env.module.colony_states["verdant"]
    aurum_state = game_env.module.colony_states["aurum"]
    before = aurum_state.need_satisfaction
    game_env.load(ship_id="2")
    game_env.depart("aurum", ship_id="2")
    game_env.tick(game_env.module.TRAVEL_TICKS)
    assert aurum_state.need_satisfaction > before
    assert verdant_state.need_satisfaction != before  # unaffected colony, sanity check it's tracked separately


def test_delivering_the_wrong_good_does_not_raise_satisfaction(game_env):
    # Ship 1 carries ore from aurum to verdant -- verdant needs
    # machinery, not ore, so this delivery shouldn't help it.
    verdant_state = game_env.module.colony_states["verdant"]
    before = verdant_state.need_satisfaction
    game_env.load(ship_id="1")
    game_env.depart("verdant", ship_id="1")
    game_env.tick(game_env.module.TRAVEL_TICKS)
    # verdant decays a little from ticking but gets no delivery boost
    assert verdant_state.need_satisfaction <= before


def test_render_shows_need_satisfaction_percentage(game_env):
    game_env.module.render()
    text = game_env.elements["colony-aurum-need-display"].innerText
    assert "50%" in text


def test_render_shows_flavor_text(game_env):
    assert game_env.elements["colony-aurum-flavor"].innerText == game_env.module.COLONY_FLAVOR["aurum"]


def test_render_updates_need_bar_width(game_env):
    game_env.module.colony_states["aurum"].need_satisfaction = 0.8
    game_env.module.render()
    assert game_env.elements["colony-aurum-need-bar"].style.width == "80%"
