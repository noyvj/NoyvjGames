"""GF-20 farm event cards: drawing, the two effects, eligibility and the buttons on the page."""
from unittest.mock import patch

from herd_model import FarmState
from herd_rules import EVENT_BUY_PRICE, EVENT_SELL_PRICE, EVENT_UNITS, FARM_EVENTS


def _event(event_id):
    return next(e for e in FARM_EVENTS if e["id"] == event_id)


def test_draw_event_sets_active_when_chance_met():
    farm = FarmState()
    farm.herd_size = 4
    with patch("herd_model.random.random", return_value=0.1):
        farm.draw_event()
    assert farm.event_active is True
    assert farm.event_data in FARM_EVENTS
    assert farm.event_choice_made is False


def test_draw_event_clears_when_chance_missed():
    farm = FarmState()
    farm.event_active = True
    with patch("herd_model.random.random", return_value=0.9):
        farm.draw_event()
    assert farm.event_active is False
    assert farm.event_data is None


def test_selling_event_is_not_drawn_without_enough_herd():
    farm = FarmState()
    farm.herd_size = EVENT_UNITS - 1
    farm.funds = 0
    with patch("herd_model.random.random", return_value=0.1):
        farm.draw_event()
    assert farm.event_active is False  # nothing the farm can take is on offer


def test_sell_units_trades_herd_for_funds():
    farm = FarmState()
    farm.herd_size = 5
    funds = farm.funds
    assert farm.apply_event_effect("sell_units") is True
    assert farm.herd_size == 5 - EVENT_UNITS
    assert farm.funds == funds + EVENT_SELL_PRICE


def test_sell_units_refused_when_herd_too_small():
    farm = FarmState()
    farm.herd_size = 1
    funds = farm.funds
    assert farm.apply_event_effect("sell_units") is False
    assert (farm.herd_size, farm.funds) == (1, funds)


def test_buy_units_trades_funds_for_herd_and_logs_the_purchase():
    farm = FarmState()
    funds = farm.funds
    assert farm.apply_event_effect("buy_units") is True
    assert farm.herd_size == EVENT_UNITS
    assert farm.funds == funds - EVENT_BUY_PRICE
    assert farm.lever_log[-1][1:] == ["herd", float(EVENT_BUY_PRICE)]


def test_buy_units_refused_when_funds_too_low():
    farm = FarmState()
    farm.funds = EVENT_BUY_PRICE - 1
    assert farm.apply_event_effect("buy_units") is False
    assert farm.herd_size == 0
    assert farm.funds == EVENT_BUY_PRICE - 1


def test_refusing_always_possible_and_changes_nothing():
    farm = FarmState()
    farm.funds = 0
    assert farm.event_effect_possible(None) is True
    assert farm.apply_event_effect(None) is True
    assert (farm.funds, farm.herd_size) == (0, 0)


def test_card_shows_after_advance_and_buttons_work(game_env):
    farm = game_env.farm
    farm.herd_size = 4
    with patch("herd_model.random.random", return_value=0.0), patch(
        "herd_model.random.choice", side_effect=lambda items: items[0]
    ):
        game_env.advance_round()
    assert game_env.elements["farm-event-card"].hidden is False
    assert game_env.elements["event-text"].innerText == _event("neighbour_buy")["text"]
    herd = game_env.farm.herd_size
    funds = game_env.farm.funds
    # the page passes the click event to the handler; a handler without a parameter would raise here
    game_env.elements["event-choice-a"].dispatch("click", object())
    assert game_env.farm.herd_size == herd - EVENT_UNITS
    assert game_env.farm.funds == funds + EVENT_SELL_PRICE
    assert game_env.elements["farm-event-card"].hidden is True


def test_refuse_button_closes_the_card_without_a_change(game_env):
    game_env.farm.herd_size = 4
    with patch("herd_model.random.random", return_value=0.0), patch(
        "herd_model.random.choice", side_effect=lambda items: items[0]
    ):
        game_env.advance_round()
    herd, funds = game_env.farm.herd_size, game_env.farm.funds
    game_env.elements["event-choice-b"].dispatch("click", object())
    assert (game_env.farm.herd_size, game_env.farm.funds) == (herd, funds)
    assert game_env.elements["farm-event-card"].hidden is True


def test_event_is_never_saved(game_env):
    game_env.farm.event_active = True
    game_env.farm.event_data = FARM_EVENTS[0]
    state = game_env.module.get_state()
    assert not any("event" in key for key in state)
