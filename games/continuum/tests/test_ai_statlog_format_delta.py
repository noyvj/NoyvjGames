"""Tests for statlog.format_delta()."""

import statlog


def test_positive_int_delta():
    assert statlog.format_delta("population", 5) == "▲ +5"


def test_negative_pct_delta():
    assert statlog.format_delta("fed_pct", -12.3) == "▼ −12%"


def test_positive_num_delta():
    assert statlog.format_delta("livability", 3.456) == "▲ +3.5"


def test_zero_delta_returns_dash():
    assert statlog.format_delta("livability", 0.0) == "▬ 0"
