"""Tests for plan.fuel_of()."""

import plan


def test_fuel_of_counts_burns_only():
    """Normal case: sum of dv values from burns when pass is empty."""
    p = {"burns": [{"t": 0, "at": "time", "head": 0.0, "dv": 1.5}, {"t": 10, "at": "time", "head": 90.0, "dv": 0.2}], "pass": {}}
    assert plan.fuel_of(p) == 1.7


def test_fuel_of_includes_pass_burns():
    """Normal case: sum of dv from burns plus absolute values of pass burns."""
    p = {"burns": [{"t": 0, "at": "time", "head": 0.0, "dv": 0.5}], "pass": {"moon": -0.3, "mars": 0.1}}
    assert plan.fuel_of(p) == 0.9


def test_fuel_of_empty_plan_returns_zero():
    """Edge case: a plan with no burns and no pass burns costs nothing."""
    assert plan.fuel_of(plan.empty()) == 0.0
