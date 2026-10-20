"""Tests for orders.action_text()."""

import orders


def rule_with(**changes):
    """Build a test rule by overriding defaults on a fresh rule."""
    rule = orders.fresh_rule(1)
    rule.update(changes)
    return rule


def test_action_text_shift_one_person():
    """Normal case: shifting exactly one person uses singular 'person'."""
    rule = rule_with(action="shift", n=1, **{"from": orders.NO_SOURCE}, to="foragers")
    expected = f"move up to 1 person from {orders.role_name(rule['from'])} to {orders.role_name(rule['to'])}"
    assert orders.action_text(rule) == expected


def test_action_text_shift_multiple_people():
    """Normal case: shifting multiple people uses plural 'people'."""
    rule = rule_with(action="shift", n=3, **{"from": "gatherers"}, to="keepers")
    expected = f"move up to 3 people from {orders.role_name(rule['from'])} to {orders.role_name(rule['to'])}"
    assert orders.action_text(rule) == expected


def test_action_text_refactor_and_notice():
    """Normal cases: non-shift actions return their fixed strings."""
    assert orders.action_text(rule_with(action="refactor")) == "schedule a refactor season"
    assert orders.action_text(rule_with(action="notice")) == "log a notice"


def test_action_text_shift_from_largest_group():
    """Edge case: using LARGEST as the source role resolves correctly."""
    rule = rule_with(action="shift", n=2, **{"from": orders.LARGEST}, to="crafters")
    expected = f"move up to 2 people from {orders.role_name(rule['from'])} to {orders.role_name(rule['to'])}"
    assert orders.action_text(rule) == expected
