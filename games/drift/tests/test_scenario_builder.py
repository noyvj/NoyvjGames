"""Tests for I-2: Scenario Builder."""

import drift_model_region as region_module
import drift_runstate as runstate


def test_scenario_constants_exist():
    from drift_rules import (
        SCENARIO_HORIZONS, SCENARIO_MIN_CAPACITY, SCENARIO_MAX_CAPACITY,
        SCENARIO_MIN_INCOME, SCENARIO_MAX_INCOME, SCENARIO_MIN_SEVERITY_RATE,
        SCENARIO_MAX_SEVERITY_RATE,
    )
    assert SCENARIO_HORIZONS == [50, 100, 150]
    assert SCENARIO_MIN_CAPACITY == 0
    assert SCENARIO_MAX_CAPACITY == 100
    assert SCENARIO_MIN_INCOME == 0
    assert SCENARIO_MAX_INCOME == 200
    assert SCENARIO_MIN_SEVERITY_RATE == 0.0
    assert SCENARIO_MAX_SEVERITY_RATE == 2.0


def test_start_scenario_applies_values():
    # Save original state to restore later
    orig_funds = region_module.region.funds
    orig_capacity = dict(region_module.region.capacity)
    orig_severity_rise = getattr(region_module.region, "severity_rise_override", None)
    orig_horizon = getattr(region_module.region, "horizon_target", None)
    orig_scenario_custom_run = runstate.scenario_custom_run

    region_module.start_scenario(
        starting_capacity={"housing": 20, "services": 15, "infrastructure": 10},
        starting_funds=400.0,
        severity_rise_override=1.0,
        horizon_target=100,
    )

    assert region_module.region.funds == 400.0
    assert region_module.region.capacity["housing"] == 20
    assert region_module.region.capacity["services"] == 15
    assert region_module.region.capacity["infrastructure"] == 10
    assert region_module.region.severity_rise_override == 1.0
    assert region_module.region.horizon_target == 100
    assert runstate.scenario_custom_run is True

    # Restore original state
    region_module.region.funds = orig_funds
    region_module.region.capacity = orig_capacity
    if orig_severity_rise is not None:
        region_module.region.severity_rise_override = orig_severity_rise
    else:
        delattr(region_module.region, "severity_rise_override")
    if orig_horizon is not None:
        region_module.region.horizon_target = orig_horizon
    else:
        delattr(region_module.region, "horizon_target")
    runstate.scenario_custom_run = orig_scenario_custom_run


def test_scenario_custom_run_flag():
    assert hasattr(runstate, "scenario_custom_run")
    assert isinstance(runstate.scenario_custom_run, bool)
