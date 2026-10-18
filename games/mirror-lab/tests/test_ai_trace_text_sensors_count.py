"""Tests for sensors_count() in trace_text.py."""

import trace_text


def test_sensors_count_plural_when_need_is_greater_than_one():
    """Normal case: plural 'sensors' when need > 1."""
    assert trace_text.sensors_count(2, 3) == "2 of 3 sensors"
    assert trace_text.sensors_count(0, 5) == "0 of 5 sensors"


def test_sensors_count_singular_when_need_is_one():
    """Normal case: singular 'sensor' when need == 1."""
    assert trace_text.sensors_count(1, 1) == "1 of 1 sensor"
    assert trace_text.sensors_count(0, 1) == "0 of 1 sensor"


def test_sensors_count_edge_case_zero_needed():
    """Edge case: when no sensors are needed (need == 0), it defaults to plural."""
    assert trace_text.sensors_count(0, 0) == "0 of 0 sensors"
