"""Iteration Pass 3 (Fun/Teaching Balance): confirmation pass on the
single-item vignette added in Pass 2. The design doc's risk here is dry
abstraction — the flow-chain graph is where the strategy lives, and the
vignette is supposed to be where the player *feels* what that strategy
means. That only holds if the vignette updates immediately (no delay)
and reacts to the actual decisions that drive circular_fraction_this_cycle()
(circularity investment + trade-link imports), not just static flavor
text. These tests lock that behavior in as a permanent regression check.
No code changes were needed — the vignette already satisfied this bar.
"""

import pytest


def test_vignette_starts_at_straight_line_message(game_env):
    game_env.module.render()
    text = game_env.elements["vignette-display"].innerText
    assert "Nothing about it comes back" in text


def test_vignette_updates_immediately_on_circularity_investment_click(game_env):
    # No advance_cycle() in between — the click handler itself must call
    # render() synchronously for this to be "immediate, felt feedback"
    # rather than feedback that lags a cycle behind the decision.
    game_env.module.render()
    before = game_env.elements["vignette-display"].innerText

    game_env.elements["recycle-invest-button"].dispatch("click", None)

    after = game_env.elements["vignette-display"].innerText
    assert after != before
    assert "Nothing about it comes back" not in after


def test_vignette_updates_immediately_on_trade_link_investment_click(game_env):
    # Imported supply counts toward circular_fraction_this_cycle() too
    # (see circular_supply()), so the trade-link button should move the
    # vignette just as directly as an internal circularity investment.
    game_env.module.render()
    before = game_env.elements["vignette-display"].innerText

    game_env.chain.funds = 1000.0
    game_env.elements["trade-link-invest-button"].dispatch("click", None)

    after = game_env.elements["vignette-display"].innerText
    assert after != before


def test_vignette_reflects_current_fraction_not_a_stale_value(game_env):
    # The vignette text shown after render() must always match what
    # vignette_message() produces for the chain's *current* fraction —
    # confirming it tracks live strategy state rather than a cached or
    # delayed snapshot from a previous cycle.
    game_env.chain.funds = 1000.0
    for _ in range(6):
        game_env.chain.invest_circularity("recycle")
    game_env.module.render()

    current_fraction = game_env.chain.circular_fraction_this_cycle()
    assert game_env.elements["vignette-display"].innerText == (
        game_env.module.vignette_message(current_fraction)
    )


def test_vignette_does_not_require_advance_cycle_to_reflect_investment(game_env):
    # The vignette must not be gated behind "end the cycle" — it should
    # already reflect a decision the moment it's made, same round.
    game_env.chain.funds = 1000.0
    for _ in range(10):
        game_env.chain.invest_circularity("recycle")
    game_env.module.render()

    text = game_env.elements["vignette-display"].innerText
    assert "recycled" in text  # fully-closed tier, reached without advance_cycle()
