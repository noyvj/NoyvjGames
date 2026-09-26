"""G15: permafrost restoration once the feedback loop is held down."""


def _melting_region(r, preserve=8, temp=12.0):
    """A melting region whose investment dampening keeps acceleration low."""
    r.capacity["preserve"] = preserve
    r.temperature = temp
    r.melt_started_round = 1
    r.counterfactual_temperature = temp


def _step(r, n=1):
    for _ in range(n):
        r.advance_round()


def test_no_restoration_before_melt(game_env):
    r = game_env.region
    r.capacity["preserve"] = 8
    _step(r, 5)
    assert r.stabilized_rounds == 0 and r.restored_total == 0.0


def test_no_restoration_without_dampening_holding_the_loop(game_env):
    r = game_env.region
    _melting_region(r, preserve=0, temp=14.0)
    _step(r, 6)
    assert r.stabilized_rounds == 0
    assert r.restored_total == 0.0


def test_streak_builds_then_restoration_starts(game_env):
    m = game_env.module
    r = game_env.region
    _melting_region(r)
    _step(r, m.RESTORATION_STREAK_ROUNDS - 1)
    assert r.restored_total == 0.0 and not r.restoration_active()
    _step(r)
    assert r.restoration_active()
    assert r.restored_total > 0.0
    assert "restoration" in r.round_events


def test_restoration_event_fires_once(game_env):
    m = game_env.module
    r = game_env.region
    _melting_region(r)
    _step(r, m.RESTORATION_STREAK_ROUNDS)
    assert "restoration" in r.round_events
    _step(r)
    assert "restoration" not in r.round_events


def test_restoration_amount_scales_with_preserve_and_is_capped(game_env):
    m = game_env.module
    a, b = m.region_b, m.region_c
    _melting_region(a, preserve=9)
    _melting_region(b, preserve=14)
    _step(a, m.RESTORATION_STREAK_ROUNDS)
    _step(b, m.RESTORATION_STREAK_ROUNDS)
    assert 0 < a.restored_total < b.restored_total
    per_round = b.restored_total  # one restoring round so far
    assert per_round <= m.RESTORATION_MAX_PER_ROUND + 1e-9


def test_restoration_never_pulls_below_melt_threshold(game_env):
    m = game_env.module
    r = game_env.region
    _melting_region(r, preserve=14, temp=10.05)
    r.temperature = 10.05
    r.stabilized_rounds = m.RESTORATION_STREAK_ROUNDS
    r._apply_restoration()
    assert r.temperature >= m.MELT_THRESHOLD - 1e-9


def test_restoration_slows_warming_versus_none(game_env):
    m = game_env.module
    a, b = m.region_b, m.region_c
    _melting_region(a)
    _melting_region(b)
    b.stabilized_rounds = 0
    a.stabilized_rounds = m.RESTORATION_STREAK_ROUNDS
    _step(a, 4)
    b._apply_restoration = lambda: None  # same region, restoration switched off
    _step(b, 4)
    assert a.temperature < b.temperature


def test_streak_resets_when_loop_gets_away(game_env):
    m = game_env.module
    r = game_env.region
    _melting_region(r)
    _step(r, m.RESTORATION_STREAK_ROUNDS)
    assert r.stabilized_rounds >= m.RESTORATION_STREAK_ROUNDS
    r.temperature = 30.0
    r.capacity["preserve"] = 0
    _step(r)
    assert r.stabilized_rounds == 0
    assert not r.restoration_active()


def test_a_temporary_rescue_does_not_count_toward_stabilization(game_env):
    r = game_env.region
    r.temperature = 17.0
    r.melt_started_round = 1
    r.funds = 500.0
    assert r.rescue()
    _step(r, 3)
    assert r.stabilized_rounds == 0


def test_status_line_visibility(game_env):
    m = game_env.module
    el = game_env.elements["restoration-status"]
    m.render()
    assert el.hidden is True
    r = game_env.region
    _melting_region(r)
    _step(r, m.RESTORATION_STREAK_ROUNDS)
    m.render()
    assert el.hidden is False and "Restoration under way" in el.innerText
    r.stabilized_rounds = 0
    m.render()
    assert "paused" in el.innerText


def test_secondary_status_line(game_env):
    m = game_env.module
    _melting_region(m.region_b)
    _step(m.region_b, m.RESTORATION_STREAK_ROUNDS)
    m.render()
    assert game_env.elements["b-restoration-status"].hidden is False
    assert game_env.elements["c-restoration-status"].hidden is True


def test_science_log_records_restoration_start(game_env):
    m = game_env.module
    r = game_env.region
    _melting_region(r)
    _step(r, m.RESTORATION_STREAK_ROUNDS)
    m._record_round_events()
    assert any("restoration" in e["text"] for e in m.science_log)


def test_save_round_trip(game_env):
    m = game_env.module
    r = game_env.region
    _melting_region(r)
    _step(r, m.RESTORATION_STREAK_ROUNDS + 1)
    data = m.get_state()
    assert data["region"]["stabilized_rounds"] == r.stabilized_rounds
    saved_total = r.restored_total
    r.stabilized_rounds = 0
    r.restored_total = 0.0
    m.load_state(data)
    assert r.stabilized_rounds == data["region"]["stabilized_rounds"]
    assert abs(r.restored_total - saved_total) < 1e-9


def test_fresh_save_omits_restoration_fields(game_env):
    data = game_env.module.get_state()["region"]
    assert "stabilized_rounds" not in data and "restored_total" not in data


def test_load_rejects_bad_values(game_env):
    m = game_env.module
    for bad_streak, bad_total in (("x", "y"), (-1, -5), (True, True), (1e9, 1e12), (None, float("nan")), (2.5, float("inf"))):
        data = m.get_state()
        data["region"]["stabilized_rounds"] = bad_streak
        data["region"]["restored_total"] = bad_total
        m.load_state(data)
        assert game_env.region.stabilized_rounds == 0
        assert game_env.region.restored_total == 0.0
