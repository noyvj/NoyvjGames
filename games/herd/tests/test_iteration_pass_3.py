"""Iteration Pass 3 (fun/teaching-balance audit), from
`climate-games-fun-teaching-balance.md`. Risk: if the coupling-ratio
mechanic were tracked as a separate "sustainability score" bolted onto an
otherwise-normal farm sim, a player could optimize pure profitability
while ignoring it entirely (chocolate-covered broccoli). Fix/check: confirm
coupling_ratio() feeds directly into the SAME profitability number the
player is trying to maximize (score()), not a parallel or optional metric.

Audit finding: already satisfied, via two independent paths from
coupling_ratio() into score() -- see CLAUDE.md's Pass 3 notes for the full
trace. These tests isolate each path so a future change that severs either
one fails loudly, rather than this "single most important check" only
ever having been an audit note.
"""

import pytest


def test_lower_coupling_ratio_directly_increases_score_at_equal_herd_size(game_env):
    # Isolate the ratio's effect on score() by setting decoupling
    # investment directly (no cost paid), so herd size, funds, and round
    # count are identical between the two farms -- only coupling_ratio()
    # differs. If score() ever stopped reading from the coupling ratio,
    # this would fail.
    coupled = game_env.module.FarmState()
    coupled.herd_size = 10
    coupled.advance_round()

    decoupled = game_env.module.FarmState()
    decoupled.herd_size = 10
    decoupled.decoupling_investment["capture"] = 5
    assert decoupled.coupling_ratio() < coupled.coupling_ratio()
    decoupled.advance_round()

    assert decoupled.score() > coupled.score()


def test_score_formula_explicitly_penalizes_methane(game_env):
    # score() is funds minus methane * METHANE_PENALTY_WEIGHT -- the
    # coupling-driven methane total is baked directly into the same
    # number as funds, not displayed as a separate/cosmetic gauge.
    farm = game_env.farm
    funds_only = farm.funds
    farm.methane = 50.0
    assert farm.score() == funds_only - 50.0 * game_env.module.METHANE_PENALTY_WEIGHT
    assert farm.score() < funds_only


def test_coupling_ratio_also_drags_down_raw_funds_via_income_pressure(game_env):
    # A second, independent path: a higher coupling ratio -> more sustained
    # methane -> higher pressure_fraction() -> less income added to funds
    # each round. This holds even before score()'s explicit penalty term
    # is applied, so the connection isn't just the one subtraction at the
    # end -- it's load-bearing earlier in the calculation too.
    # Kept well under MAX_PRESSURE's cap (both farms would otherwise
    # saturate at the same 0.8 ceiling and the difference would vanish).
    high_ratio = game_env.module.FarmState()
    high_ratio.herd_size = 10
    for _ in range(6):
        high_ratio.advance_round()

    low_ratio = game_env.module.FarmState()
    low_ratio.herd_size = 10
    low_ratio.decoupling_investment["capture"] = 5  # set directly, no cost paid
    for _ in range(6):
        low_ratio.advance_round()

    assert low_ratio.pressure_fraction() < high_ratio.pressure_fraction()
    assert low_ratio.funds > high_ratio.funds


def test_decoupled_growth_is_the_actual_winning_strategy_within_a_normal_session(game_env):
    # Regression guard for the doc's framing: "the winning strategy and
    # the decoupling lesson need to be the same strategy, full stop."
    # Uses real invest_decoupling() (cost paid) so this reflects an actual
    # playthrough, not an isolated field tweak like the tests above.
    pure_growth = game_env.module.FarmState()
    for _ in range(6):
        pure_growth.grow_herd()
    for _ in range(15):
        pure_growth.advance_round()

    decoupled_growth = game_env.module.FarmState()
    for _ in range(6):
        decoupled_growth.grow_herd()
    for _ in range(5):
        decoupled_growth.invest_decoupling("capture")
    for _ in range(15):
        decoupled_growth.advance_round()

    assert decoupled_growth.herd_size == pure_growth.herd_size  # same growth choices
    assert decoupled_growth.score() > pure_growth.score()  # decoupling wins on THE score
