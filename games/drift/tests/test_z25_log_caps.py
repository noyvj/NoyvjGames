"""Z25 save-payload audit: arrivals_log/strain_log/wellbeing_log/
subscore_log previously grew by one entry per round with no cap at all.
strain_log has two real consumers that need the FULL history, not a
recent window -- average_strain()'s lifetime average and the "ever
reached critical strain" achievement gate -- so both were decoupled from
the raw list (RegionState._strain_sum/_strain_count/_ever_critical_strain,
updated once per round alongside the now-capped append) before all four
logs were capped at DRIFT_LOG_MAX_ENTRIES. These tests are regression
guards for that decoupling, not just "doesn't crash" smoke tests.
"""

import pytest


def _run_rounds(game_env, count):
    for _ in range(count):
        game_env.advance_round()


def test_all_four_logs_stay_capped_after_many_rounds(game_env):
    module = game_env.module
    region = game_env.region
    cap = module.DRIFT_LOG_MAX_ENTRIES

    _run_rounds(game_env, cap + 75)

    assert len(region.arrivals_log) == cap
    assert len(region.strain_log) == cap
    assert len(region.wellbeing_log) == cap
    assert len(region.subscore_log) == cap


def test_average_strain_correct_after_the_log_itself_gets_capped(game_env):
    """Regression guard for the _strain_sum/_strain_count decoupling:
    average_strain() must keep returning the true lifetime average once
    strain_log itself has been truncated to the last DRIFT_LOG_MAX_ENTRIES
    rounds, not silently degrade into a rolling-window average over
    whatever happens to still be in the capped list."""
    module = game_env.module
    region = game_env.region
    cap = module.DRIFT_LOG_MAX_ENTRIES

    # A little early capacity means strain starts near zero and rises
    # over time as arrivals (which grow with background severity) outrun
    # that fixed capacity -- a genuinely non-constant history, so a
    # recent-window average and a lifetime average would actually differ
    # if the bug were present.
    region.invest("housing")

    rounds = cap + 60
    expected_values = []
    for _ in range(rounds):
        # advance_round() appends exactly this pre-round strain_fraction()
        # value to strain_log -- capturing it here before advancing
        # reproduces the true full lifetime history independent of
        # whatever the (now-capped) live strain_log still holds.
        expected_values.append(region.strain_fraction())
        game_env.advance_round()

    expected_average = sum(expected_values) / len(expected_values)

    assert len(region.strain_log) == cap
    assert region.average_strain() == pytest.approx(expected_average)

    # The raw capped log alone can no longer reproduce that lifetime
    # average by direct summation -- proof the sum/count decoupling is
    # actually doing the work, not merely present and unused.
    naive_capped_average = sum(region.strain_log) / len(region.strain_log)
    assert naive_capped_average != pytest.approx(expected_average)


def test_full_recovery_achievement_survives_log_cap_rollover(game_env):
    """The 'full_recovery' achievement (_ever_reached_critical_strain()
    now-stable) must stay earnable long after the round that actually
    crossed into critical strain has rolled off strain_log's capped
    window -- proving the sticky _ever_critical_strain flag, not a scan
    over the log, is what's actually checked."""
    module = game_env.module
    region = game_env.region
    cap = module.DRIFT_LOG_MAX_ENTRIES
    critical_threshold = module.STRAIN_LEVEL_THRESHOLDS[2][0]

    # strain_fraction() is evaluated *before* this round's own arrivals
    # land, so round 1 always logs 0.0 (no arrivals have landed yet) --
    # round 2, with zero capacity anywhere, is the first round whose
    # logged strain actually reflects round 1's arrivals outrunning it,
    # maxing straight to critical (1.0 >= 0.6).
    game_env.advance_round()
    game_env.advance_round()
    assert region.strain_log[-1] >= critical_threshold
    assert region.strain_level() == "critical"

    # Recover hard and stay comfortably ahead of arrivals for well more
    # than DRIFT_LOG_MAX_ENTRIES further rounds, so round 1's critical
    # strain entry is long gone from the capped strain_log by the end.
    for _ in range(cap + 30):
        region.capacity["housing"] = region.total_arrivals + 1000.0
        game_env.advance_round()

    assert len(region.strain_log) == cap
    assert all(s < critical_threshold for s in region.strain_log)
    assert region.strain_level() == "stable"

    # A naive re-scan of the (capped) log would wrongly conclude critical
    # strain was never reached; the achievement must still be earned.
    assert "full_recovery" in module.achievement_ids_earned()


def test_load_state_old_save_missing_strain_fields_recomputes_them(game_env):
    """An old save written before this Z25 refactor has no strain_sum/
    strain_count/ever_critical_strain keys at all. load_state() must
    recompute all three from whatever strain_log that old save still
    carries (its full, not-yet-capped history), rather than defaulting
    to 0/False and silently losing the correct running average / the
    achievement-earned state."""
    module = game_env.module
    region = game_env.region

    # Build up some real strain history, including a critical round.
    # strain_fraction() is evaluated *before* this round's own arrivals
    # land, so round 1 always logs 0.0; round 2, still at zero capacity,
    # is the first round whose logged strain reflects round 1's arrivals
    # outrunning it, logging critical.
    game_env.advance_round()
    game_env.advance_round()
    region.capacity["housing"] = 500.0
    for _ in range(8):
        game_env.advance_round()  # comfortably stable from here on

    live_average = region.average_strain()
    live_strain_log = list(region.strain_log)
    assert live_average > 0.0
    assert any(s >= module.STRAIN_LEVEL_THRESHOLDS[2][0] for s in live_strain_log)

    old_save = module.get_state()
    del old_save["strain_sum"]
    del old_save["strain_count"]
    del old_save["ever_critical_strain"]

    # Diverge the live region so a successful load is actually observable.
    region.capacity["housing"] = 0.0
    region._strain_sum = 0.0
    region._strain_count = 0
    region._ever_critical_strain = False
    for _ in range(3):
        game_env.advance_round()

    result = module.load_state(old_save)

    assert result is True
    assert region.strain_log == live_strain_log
    assert region.average_strain() == pytest.approx(live_average)
    assert region._strain_count == len(live_strain_log)
    assert region._strain_sum == pytest.approx(sum(live_strain_log))
    assert region._ever_critical_strain is True
    assert "full_recovery" in module.achievement_ids_earned()


def test_load_state_fresh_save_uses_stored_strain_fields_directly(game_env):
    """The normal (non-legacy) path: a save written by the current code
    already carries strain_sum/strain_count/ever_critical_strain, and
    load_state() should just restore them rather than recomputing --
    recomputing here would also happen to be correct since strain_log
    round-trips intact, but this pins the "use what's there" branch
    explicitly."""
    module = game_env.module
    region = game_env.region

    game_env.advance_round()
    region.capacity["housing"] = 500.0
    for _ in range(5):
        game_env.advance_round()

    snapshot = module.get_state()
    assert "strain_sum" in snapshot
    assert "strain_count" in snapshot
    assert "ever_critical_strain" in snapshot

    region.capacity["housing"] = 0.0
    for _ in range(3):
        game_env.advance_round()
    assert module.get_state() != snapshot

    result = module.load_state(snapshot)

    assert result is True
    assert region._strain_sum == snapshot["strain_sum"]
    assert region._strain_count == snapshot["strain_count"]
    assert region._ever_critical_strain == snapshot["ever_critical_strain"]
