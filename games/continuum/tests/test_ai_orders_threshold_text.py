"""Tests for threshold_text() in orders.py."""

import orders


def test_threshold_text_plural_seasons():
    """Normal plural case returns the correct unit string."""
    assert orders.threshold_text("food_seasons", 2) == "2 seasons of eating"


def test_threshold_text_singular_season_edge_case():
    """Edge case: value 1 replaces 'seasons' with 'season'."""
    assert orders.threshold_text("food_seasons", 1) == "1 season of eating"


def test_threshold_text_empty_unit():
    """Normal case with an empty unit string returns just the number."""
    assert orders.threshold_text("idle", 5) == "5"


def test_threshold_text_percentage_unit():
    """Normal case with a percentage unit appends '%'."""
    assert orders.threshold_text("land_health", 50) == "50%"
