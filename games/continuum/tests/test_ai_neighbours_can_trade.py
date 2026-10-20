"""Tests for neighbours.can_trade()."""


import neighbours


def test_can_trade_returns_true_when_cooldown_passed_and_resources_available():
    """Normal case: cooldown passed and resources available."""
    record = neighbours.default()
    ok, reason = neighbours.can_trade(record, "n1", 1, {"food": 10.0, "materials": 10.0, "knowledge": 10.0}, 0)
    assert ok is True
    assert reason == ""


def test_can_trade_returns_false_when_cooldown_not_passed():
    """Normal case: cooldown not passed."""
    record = neighbours.default()
    record["slots"]["n1"]["next_trade"] = 50
    ok, reason = neighbours.can_trade(record, "n1", 10, {"food": 10.0, "materials": 10.0, "knowledge": 10.0}, 0)
    assert ok is False
    assert "will trade again" in reason


def test_can_trade_returns_false_when_insufficient_resources():
    """Normal case: insufficient resources."""
    record = neighbours.default()
    ok, reason = neighbours.can_trade(record, "n1", 1, {"food": 0.0, "materials": 0.0, "knowledge": 0.0}, 0)
    assert ok is False
    assert "You need" in reason


def test_can_trade_returns_false_for_invalid_slot():
    """Edge case: invalid slot ID."""
    record = neighbours.default()
    ok, reason = neighbours.can_trade(record, "n99", 1, {"food": 10.0, "materials": 10.0, "knowledge": 10.0}, 0)
    assert ok is False
    assert reason == "No such neighbour."
