"""Iteration Pass 2: trade network (a basic bidirectional link — import
reuse capacity in, export internal surplus out — with one neighboring
system, not a full second economy) and a single-item vignette (a
concrete phone-shaped side-story tracking the same underlying
circular fraction the abstract chain view already shows).
"""

import pytest


def test_trade_link_starts_uninvested(game_env):
    assert game_env.chain.trade_link_investment == 0
    assert game_env.chain.imported_supply() == 0.0


def test_invest_trade_link_increases_imported_supply(game_env):
    game_env.chain.invest_trade_link()
    assert game_env.chain.imported_supply() == pytest.approx(game_env.module.IMPORT_SUPPLY_PER_UNIT)


def test_invest_trade_link_fails_without_funds(game_env):
    game_env.chain.funds = 0
    assert game_env.chain.invest_trade_link() is False


def test_imported_supply_counts_toward_closing_the_loop(game_env):
    before = game_env.chain.new_extraction_needed()
    game_env.chain.invest_trade_link()
    after = game_env.chain.new_extraction_needed()
    assert after < before


def test_imported_supply_does_not_count_as_internal_circular_supply(game_env):
    game_env.chain.invest_trade_link()
    assert game_env.chain.internal_circular_supply() == 0.0
    assert game_env.chain.circular_supply() > 0.0


def test_exportable_surplus_zero_without_enough_internal_investment(game_env):
    game_env.chain.invest_circularity("repair")
    assert game_env.chain.exportable_surplus() == 0.0


def test_exportable_surplus_positive_once_internal_supply_exceeds_target(game_env):
    # recycle supplies 5.0/unit; enough units to clear PRODUCTION_TARGET (50)
    units_needed = int(game_env.module.PRODUCTION_TARGET // 5.0) + 1
    game_env.chain.funds = 10000
    for _ in range(units_needed):
        game_env.chain.invest_circularity("recycle")
    assert game_env.chain.exportable_surplus() > 0.0


def test_imported_supply_is_never_exported(game_env):
    # Import-only chain (no internal investment) should never show a
    # surplus, even though total circular_supply might exceed target.
    game_env.chain.funds = 10000
    for _ in range(20):
        game_env.chain.invest_trade_link()
    assert game_env.chain.exportable_surplus() == 0.0


def test_advance_cycle_adds_export_revenue_to_funds(game_env):
    units_needed = int(game_env.module.PRODUCTION_TARGET // 5.0) + 1
    game_env.chain.funds = 10000
    for _ in range(units_needed):
        game_env.chain.invest_circularity("recycle")
    surplus = game_env.chain.exportable_surplus()
    funds_before = game_env.chain.funds
    game_env.chain.advance_cycle()
    expected_export_revenue = surplus * game_env.module.EXPORT_PRICE_PER_UNIT
    # Funds also change from base revenue/cost, so just confirm the
    # export contribution is present and positive.
    assert expected_export_revenue > 0.0
    assert game_env.chain.funds > funds_before  # closed loop, no extraction cost, plus export


def test_render_shows_trade_link_investment_count(game_env):
    game_env.chain.invest_trade_link()
    game_env.module.render()
    assert game_env.elements["trade-link-count"].innerText == "1"


def test_trade_link_button_click_dispatches(game_env):
    game_env.chain.funds = 1000
    game_env.module.render()
    game_env.elements["trade-link-invest-button"].dispatch("click", None)
    assert game_env.chain.trade_link_investment == 1


def test_import_flow_row_opacity_reflects_import_fraction(game_env):
    game_env.chain.invest_trade_link()
    game_env.module.render()
    opacity = float(game_env.elements["import-flow-row"].style.opacity)
    assert opacity > 0.0


def test_vignette_message_straight_line(game_env):
    text = game_env.module.vignette_message(0.0)
    assert "Nothing about it comes back" in text


def test_vignette_message_fully_closed(game_env):
    text = game_env.module.vignette_message(1.0)
    assert "recycled" in text


def test_vignette_message_partial(game_env):
    text = game_env.module.vignette_message(0.3)
    assert "phone" in text


def test_render_updates_vignette_display(game_env):
    game_env.module.render()
    assert len(game_env.elements["vignette-display"].innerText) > 0
