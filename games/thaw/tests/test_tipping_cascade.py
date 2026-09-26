"""G5: the tipping cascade (deterministic pseudo-random chance)."""


def _force(module, chance):
    module.CASCADE_CHANCE = chance


def _tip(r):
    """Puts a region one round short of melting."""
    r.temperature = 9.5


def test_roll_is_deterministic_and_in_range(game_env):
    m = game_env.module
    for label in "ABC":
        for rnd in range(1, 60):
            v = m.cascade_roll(label, rnd)
            assert 0.0 <= v < 1.0
            assert v == m.cascade_roll(label, rnd)


def test_roll_varies_across_rounds_and_sources(game_env):
    m = game_env.module
    values = {m.cascade_roll(label, rnd) for label in "AB" for rnd in range(1, 40)}
    assert len(values) > 20


def test_certain_cascade_bumps_the_next_region(game_env):
    m = game_env.module
    _force(m, 1.01)
    _tip(m.region)
    before = (m.region_b.temperature, m.region_b.counterfactual_temperature)
    game_env.advance_round()
    rise = m.BASE_TEMP_RISE_PER_ROUND
    assert abs(m.region_b.temperature - (before[0] + rise + m.CASCADE_BUMP)) < 1e-9
    assert abs(m.region_b.counterfactual_temperature - (before[1] + rise + m.CASCADE_BUMP)) < 1e-9
    assert "cascade" in m.region_b.round_events


def test_no_cascade_when_the_roll_fails(game_env):
    m = game_env.module
    _force(m, 0.0)
    _tip(m.region)
    game_env.advance_round()
    assert "cascade" not in m.region_b.round_events
    assert abs(m.region_b.temperature - m.BASE_TEMP_RISE_PER_ROUND) < 1e-9


def test_only_the_round_melt_starts_can_cascade(game_env):
    m = game_env.module
    _force(m, 1.01)
    _tip(m.region)
    game_env.advance_round()  # A tips, B cascaded once
    assert "cascade" in m.region_b.round_events
    game_env.advance_round()  # A is already melting: no fresh tip, no new bump
    assert "cascade" not in m.region_b.round_events


def test_chain_is_one_way_a_to_b_to_c(game_env):
    m = game_env.module
    _force(m, 1.01)
    _tip(m.region_c)
    game_env.advance_round()
    assert "cascade" not in m.region.round_events
    assert "cascade" not in m.region_b.round_events
    assert "cascade" not in m.region_c.round_events


def test_b_tipping_cascades_onto_c(game_env):
    m = game_env.module
    _force(m, 1.01)
    _tip(m.region_b)
    game_env.advance_round()
    assert "cascade" in m.region_c.round_events


def test_region_a_and_d_never_receive(game_env):
    m = game_env.module
    _force(m, 1.01)
    for r in (m.region, m.region_b, m.region_c):
        _tip(r)
    for _ in range(5):
        game_env.advance_round()
        assert "cascade" not in m.region.round_events
    # Region D still equals Region A's counterfactual exactly.
    assert abs(m.region_d.temperature - m.region.counterfactual_temperature) < 1e-6


def test_cascade_does_not_change_degrees_saved(game_env):
    m = game_env.module
    _force(m, 1.01)
    _tip(m.region)
    saved_before = m.region_b.temperature_saved()
    game_env.advance_round()
    assert abs(m.region_b.temperature_saved() - saved_before) < 1e-9


def test_history_stays_consistent_with_temperature(game_env):
    m = game_env.module
    _force(m, 1.01)
    _tip(m.region)
    game_env.advance_round()
    assert m.region_b.temperature_history[-1] == m.region_b.temperature


def test_cascade_is_logged_to_the_science_log(game_env):
    m = game_env.module
    _force(m, 1.01)
    _tip(m.region)
    game_env.advance_round()
    assert any("cascade" in e["text"] and e["region"] == "B" for e in m.science_log)


def test_a_run_always_cascades_the_same_way(game_env):
    m = game_env.module
    outcomes = [m.cascade_roll("A", rnd) < m.CASCADE_CHANCE for rnd in range(1, 40)]
    assert outcomes == [m.cascade_roll("A", rnd) < m.CASCADE_CHANCE for rnd in range(1, 40)]
    assert any(outcomes) and not all(outcomes)
