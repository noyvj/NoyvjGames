"""Bug fix (2026-09-21): `_auto_play_worst_case_region()` used to spend
Region D's funds on Output one unit at a time via `while region_d.invest
("output"): pass`. Region D's own neglect makes its capacity compound
roughly 30%/round (all income reinvested at a flat per-unit cost), so
the number of loop iterations needed each round grew exponentially with
round count too -- a long session's Advance Round click could take
seconds by round 50+. Fixed to buy the affordable unit count directly.
These tests pin the fix's correctness (same end state as the old
one-at-a-time loop) and guard against the performance regression
reappearing."""

import time


def test_auto_play_matches_one_at_a_time_investment(game_env):
    """Same funds/capacity outcome as the old loop, for a single round."""
    m = game_env.module
    region_d = m.region_d
    region_d.funds = 205.0  # 10 whole units of output at cost 20, 5 left over
    starting_capacity = region_d.capacity["output"]

    m._auto_play_worst_case_region()

    new_capacity = starting_capacity + 10
    assert region_d.capacity["output"] == new_capacity
    # advance_round() then adds this round's income on top of the 5.0
    # leftover from the spend-down.
    assert region_d.funds == 5.0 + new_capacity * 6


def test_auto_play_spends_down_to_below_one_units_cost(game_env):
    m = game_env.module
    region_d = m.region_d
    region_d.funds = 47.0
    m._auto_play_worst_case_region()
    # advance_round() has already added this round's income on top of the
    # leftover funds by the time we inspect it, so check the leftover
    # remainder is what's left of a flat division by the unit cost,
    # independent of the income added afterward.
    leftover_before_income = region_d.funds - region_d.capacity["output"] * 6
    assert leftover_before_income == 47.0 % m.INVEST_COST["output"]


def test_auto_play_never_spends_more_than_affordable(game_env):
    m = game_env.module
    region_d = m.region_d
    region_d.funds = 19.0  # less than one unit's cost (20)
    starting_capacity = region_d.capacity["output"]
    m._auto_play_worst_case_region()
    assert region_d.capacity["output"] == starting_capacity


def test_auto_play_stays_fast_across_many_rounds(game_env):
    """Regression guard for the exponential-time bug itself: 400 rounds
    used to take minutes (and climbing) as Region D's compounding
    capacity made each round's spend-down loop longer than the last;
    fixed, it's a handful of arithmetic operations per round regardless
    of how large the region has grown."""
    m = game_env.module
    start = time.time()
    for _ in range(400):
        m._auto_play_worst_case_region()
    elapsed = time.time() - start
    assert elapsed < 2.0
