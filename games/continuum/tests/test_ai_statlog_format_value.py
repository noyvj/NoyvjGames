"""Tests for statlog.format_value()."""

import statlog


def test_format_value_int():
    """An integer column like population formats without decimals."""
    assert statlog.format_value("population", 1234.9) == "1235"
    assert statlog.format_value("population", 0) == "0"


def test_format_value_pct():
    """A percentage column like land health appends a % sign and rounds."""
    assert statlog.format_value("land", 75.6) == "76%"
    assert statlog.format_value("land", 0.4) == "0%"


def test_format_value_num():
    """A numeric column like food shows one decimal place."""
    assert statlog.format_value("food", 123.45) == "123.5"
    assert statlog.format_value("food", 0) == "0.0"


def test_format_value_edge_case_unknown_kind():
    """An unknown column key falls back to 'num' formatting."""
    assert statlog.format_value("unknown_key", 42.123) == "42.1"
