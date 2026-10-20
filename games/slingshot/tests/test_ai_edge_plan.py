"""Edge-case tests for plan.py."""


import plan as planlib


def test_clean_burn_accepts_valid_input():
    """A well-formed burn dict returns a cleaned dict with correct types."""
    raw = {"t": 10, "at": "time", "head": 45.5, "dv": 1.234}
    result = planlib.clean_burn(raw, 100)
    assert result == {"t": 10, "at": "time", "head": 45.5, "dv": 1.234}


def test_clean_burn_rejects_boolean_and_string_t():
    """t must be a number; booleans and strings are rejected."""
    assert planlib.clean_burn({"t": True}, 10) is None
    assert planlib.clean_burn({"t": False}, 10) is None
    assert planlib.clean_burn({"t": "10"}, 10) is None


def test_clean_burn_rejects_out_of_bounds_head_and_dv():
    """head and dv outside their ranges are rejected (return None)."""
    raw = {"t": 5, "at": "time", "head": 200.0, "dv": 1.0}
    assert planlib.clean_burn(raw, 10) is None

    raw = {"t": 5, "at": "time", "head": -200.0, "dv": 1.0}
    assert planlib.clean_burn(raw, 10) is None

    raw = {"t": 5, "at": "time", "head": 45.0, "dv": 30.0}
    assert planlib.clean_burn(raw, 10) is None


def test_clean_burn_handles_nan_and_inf():
    """NaN and infinity for t are rejected."""
    assert planlib.clean_burn({"t": float("nan")}, 10) is None
    assert planlib.clean_burn({"t": float("inf")}, 10) is None
    assert planlib.clean_burn({"t": float("-inf")}, 10) is None


def test_clean_plan_limits_burns_to_max():
    """clean_plan truncates burns to MAX_BURNS."""
    raw = {"burns": [{"t": i, "dv": 0.1} for i in range(10)], "pass": {}}
    result = planlib.clean_plan(raw, 100)
    assert len(result["burns"]) == planlib.MAX_BURNS


def test_clean_plan_drops_zero_pass_dv():
    """A pass dv of exactly zero is dropped by clean_plan."""
    raw = {"pass": {"moon": 0.0}}
    result = planlib.clean_plan(raw, 100, children=("moon",))
    assert "moon" not in result["pass"]


def test_clean_plan_ignores_unknown_children():
    """Pass slots for unknown bodies are ignored."""
    raw = {"pass": {"unknown_moon": 0.5}}
    result = planlib.clean_plan(raw, 100, children=("moon",))
    assert result["pass"] == {}


def test_empty_returns_correct_structure():
    """empty() returns a plan with no burns and no passes."""
    result = planlib.empty()
    assert result == {"burns": [], "pass": {}}


def test_fuel_of_calculates_total_budget_spend():
    """fuel_of sums burn dv and absolute pass dv correctly."""
    p = {"burns": [{"dv": 1.0}, {"dv": 2.5}], "pass": {"moon": -0.5, "mars": 0.0}}
    assert planlib.fuel_of(p) == 4.0


def test_is_empty_detects_non_empty_plans():
    """is_empty returns False when burns or passes are present."""
    assert not planlib.is_empty({"burns": [{"dv": 0}], "pass": {}})
    assert not planlib.is_empty({"burns": [], "pass": {"moon": 0.1}})
