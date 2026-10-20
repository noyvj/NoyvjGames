"""Tests for orders.value_text()."""

import orders


def test_food_seasons_formats_one_decimal():
    assert orders.value_text("food_seasons", 2.5) == "2.5 seasons of eating"
    assert orders.value_text("food_seasons", 1.0) == "1.0 seasons of eating"


def test_percentage_triggers_round_to_integer():
    assert orders.value_text("land_health", 75.3) == "75%"
    assert orders.value_text("pollution", 20.9) == "21%"


def test_plain_numbers_format_as_integers():
    assert orders.value_text("materials", 10) == "10"
    assert orders.value_text("idle", 3.7) == "4"


def test_none_value_returns_unknown():
    assert orders.value_text("food_seasons", None) == "unknown"
