"""Tests for orders.condition_text()."""

import orders


def test_condition_text_food_below():
    rule = {"trigger": "food_seasons", "op": "below", "value": 2}
    assert orders.condition_text(rule) == "food stored is below 2 seasons of eating"


def test_condition_text_idle_above():
    rule = {"trigger": "idle", "op": "above", "value": 3}
    assert orders.condition_text(rule) == "idle people is above 3"


def test_condition_text_food_singular_season():
    rule = {"trigger": "food_seasons", "op": "below", "value": 1}
    assert orders.condition_text(rule) == "food stored is below 1 season of eating"
