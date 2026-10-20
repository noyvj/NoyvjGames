"""Tests for progress.has_tide()."""

import progress


def test_has_tide_returns_false_with_no_currents():
    """A chart without a currents key has no tide."""
    assert progress.has_tide({}) is False


def test_has_tide_returns_false_when_currents_lack_tide_key():
    """Current zones that only have set and drift_range do not trigger the flag."""
    chart = {
        "currents": [
            {"set": 180, "drift_range": (1.0, 2.0)},
            {"set": 90, "drift_range": (0.5, 1.5)},
        ]
    }
    assert progress.has_tide(chart) is False


def test_has_tide_returns_true_when_any_current_has_tide():
    """A single current zone containing a 'tide' dict makes the chart tidal."""
    chart = {
        "currents": [
            {"set": 180, "drift_range": (1.0, 2.0)},
            {"set": 90, "drift_range": (0.5, 1.5), "tide": {"period": 12, "phase": 3}},
        ]
    }
    assert progress.has_tide(chart) is True


def test_has_tide_edge_case_empty_currents_list():
    """An empty currents list should safely return False."""
    chart = {"currents": []}
    assert progress.has_tide(chart) is False
