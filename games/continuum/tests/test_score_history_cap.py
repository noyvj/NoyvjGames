"""Z25 (planning/TODO.md) — capping CityState.score_history.

CLAUDE.md's own Phase 4 audit note flagged score_history as unbounded, and
Z25's own audit found it (and every era_snapshot's own copy of it) growing
faster than linearly over a long session. Two real features read the FULL
lifetime history, not just a recent window — summary.py's peak-score/
efficiency-rank readout, and the "ever recovered from collapse" achievement
— so this suite pins that capping the raw list (record_score(), matching
log.Chronicle's own MAX_ENTRIES=60 pattern) does not silently break either
one, and that an old save from before these fields existed still works.
"""

import save
import sim


def test_record_score_appends_normally_under_the_cap():
    state = sim.CityState()
    for value in [40.0, 55.0, 70.0]:
        state.record_score(value)
    assert state.score_history == [40.0, 55.0, 70.0]


def test_record_score_trims_the_front_once_past_the_cap():
    state = sim.CityState()
    for i in range(sim.SCORE_HISTORY_MAX_ENTRIES + 10):
        state.record_score(float(i))

    assert len(state.score_history) == sim.SCORE_HISTORY_MAX_ENTRIES
    # Oldest entries (0..9) were dropped; the newest is always kept.
    assert state.score_history[0] == 10.0
    assert state.score_history[-1] == float(sim.SCORE_HISTORY_MAX_ENTRIES + 9)


def test_peak_score_survives_the_cap_even_after_its_own_entry_is_trimmed():
    state = sim.CityState()
    state.record_score(97.0)  # the real lifetime peak
    for _ in range(sim.SCORE_HISTORY_MAX_ENTRIES + 5):
        state.record_score(50.0)  # long enough to push 97.0 out of the list

    assert 97.0 not in state.score_history
    assert state.peak_score == 97.0


def test_ever_recovered_from_collapse_survives_the_cap():
    state = sim.CityState()
    state.record_score(20.0)  # collapse
    state.record_score(75.0)  # recovery -- earns the flag right here
    assert state.ever_recovered_from_collapse is True

    for _ in range(sim.SCORE_HISTORY_MAX_ENTRIES + 5):
        state.record_score(50.0)  # long enough to trim both evidence entries

    assert 20.0 not in state.score_history
    assert 75.0 not in state.score_history
    assert state.ever_recovered_from_collapse is True  # never un-earned


def test_recovery_flag_does_not_fire_out_of_order():
    state = sim.CityState()
    state.record_score(90.0)
    state.record_score(20.0)  # collapses AFTER the high point
    assert state.ever_recovered_from_collapse is False


def test_recompute_from_history_matches_a_real_replay():
    state = sim.CityState()
    values = [88.0, 25.0, 71.0, 40.0, 95.0]
    for value in values:
        state.record_score(value)
    live_peak, live_recovered = state.peak_score, state.ever_recovered_from_collapse

    replayed = sim.CityState()
    replayed.score_history = list(values)
    replayed.recompute_score_derivatives_from_history()

    assert replayed.peak_score == live_peak == 95.0
    assert replayed.ever_recovered_from_collapse == live_recovered is True


def test_loading_a_save_from_before_these_fields_existed_recomputes_them():
    """Simulates a save dict written before peak_score/lowest_score_seen/
    ever_recovered_from_collapse were added to CITY_FIELDS: it has a real
    score_history but none of the three new keys."""
    state = sim.CityState()
    old_format_city = {"score_history": [88.0, 20.0, 5.0, 71.0]}

    save.restore_city(state, old_format_city)

    assert state.score_history == [88.0, 20.0, 5.0, 71.0]
    assert state.peak_score == 88.0
    assert state.ever_recovered_from_collapse is True


def test_loading_a_save_with_no_score_history_at_all_leaves_fresh_defaults():
    state = sim.CityState()
    save.restore_city(state, {})
    assert state.score_history == []
    assert state.peak_score is None
    assert state.ever_recovered_from_collapse is False


def test_a_full_round_trip_restores_the_new_fields_directly_not_via_recompute():
    state = sim.CityState()
    state.record_score(30.0)
    state.record_score(90.0)
    snapshot = save.city_snapshot(state)
    assert snapshot["peak_score"] == 90.0
    assert snapshot["ever_recovered_from_collapse"] is False  # never dropped below 30 first

    fresh = sim.CityState()
    save.restore_city(fresh, snapshot)
    assert fresh.peak_score == 90.0
    assert fresh.score_history == state.score_history


def test_an_era_snapshot_taken_after_capping_still_reports_the_true_peak():
    """The original Z25 concern: an era_snapshots entry embeds a full copy
    of score_history at time-of-snapshot. Confirms that even once the raw
    list has been trimmed by the cap, the snapshot's own peak_score is
    still the settlement's true lifetime high, not just the max of
    whatever's left in the capped tail."""
    campaign = save.Campaign()
    campaign.state.record_score(99.0)  # the real peak, early on
    for _ in range(sim.SCORE_HISTORY_MAX_ENTRIES + 5):
        campaign.state.record_score(50.0)

    assert 99.0 not in campaign.state.score_history
    campaign.record_era_snapshot("tribal")

    assert campaign.era_snapshots["tribal"]["city"]["peak_score"] == 99.0
