"""Iteration Pass 3 (fun/teaching balance): the idle/passive side of the
plot-grid risked tipping toward boredom — if preserving mostly means
waiting, without felt decisions, flow drops even though the "restraint
compounds" lesson is technically still there. Pass 2's stakeholder-tension
requests and biodiversity sub-meter were the two built-in pacing beats
that could break up idle stretches, but they weren't paced against each
other: the first wildlife icon (the biodiversity payoff) used to land at
50 ticks, long after two stakeholder-tension cycles (every 20 ticks) had
already come and gone. This pass tightens both intervals so a felt beat
(stakeholder decision or biodiversity payoff) lands roughly every 10-15
ticks instead of leaving a 50-tick stretch with nothing new.
"""

# Pass 2's original pacing, kept here only as a reference baseline for the
# "did this actually get tighter" regression check below — not re-imported
# from game.py, since the whole point is that game.py no longer uses it.
PASS_2_STAKEHOLDER_INTERVAL_BASELINE = 20


def test_stakeholder_interval_tightened_for_pacing(game_env):
    assert game_env.module.STAKEHOLDER_EVENT_INTERVAL_TICKS < PASS_2_STAKEHOLDER_INTERVAL_BASELINE


def test_first_stakeholder_event_fires_sooner_than_pass_2_baseline(game_env):
    # Under Pass 2's original 20-tick interval, nothing would be pending
    # yet at tick 19. Under the tightened Pass 3 interval, it should
    # already have fired.
    game_env.timers.tick_intervals(PASS_2_STAKEHOLDER_INTERVAL_BASELINE - 1)
    assert game_env.module.pending_stakeholder_request is not None


def test_wildlife_unlock_paced_to_land_at_or_before_first_stakeholder_event(game_env):
    ticks_to_wildlife = int(
        game_env.module.BIODIVERSITY_WILDLIFE_THRESHOLD
        / game_env.module.BIODIVERSITY_ACCRUAL_PER_TICK
    ) + 1
    assert ticks_to_wildlife <= game_env.module.STAKEHOLDER_EVENT_INTERVAL_TICKS


def test_wildlife_icon_appears_well_before_old_pass_2_pacing(game_env):
    # Old pacing needed 50 ticks for the first wildlife icon. Confirm the
    # new pacing lands comfortably earlier than that, so a mostly-idle
    # early game gets a felt payoff instead of a long silent stretch.
    ticks_to_wildlife = int(
        game_env.module.BIODIVERSITY_WILDLIFE_THRESHOLD
        / game_env.module.BIODIVERSITY_ACCRUAL_PER_TICK
    ) + 1
    assert ticks_to_wildlife < 50
    game_env.timers.tick_intervals(ticks_to_wildlife)
    assert game_env.plot(0).has_wildlife() is True


def test_wildlife_payoff_and_stakeholder_decision_both_land_within_first_15_ticks(game_env):
    # Two distinct felt beats (a biodiversity payoff, then a decision)
    # should both have landed inside the first 15 ticks under the new
    # pacing, rather than one lone event 50 ticks in.
    game_env.timers.tick_intervals(15)
    assert game_env.plot(0).has_wildlife() is True
    assert game_env.module.pending_stakeholder_request is not None
