"""Tests for orders.role_name()."""

import orders
import sim


def test_role_name_returns_idle_people_for_no_source():
    """Edge case: NO_SOURCE constant maps to 'Idle people'."""
    assert orders.role_name(orders.NO_SOURCE) == "Idle people"


def test_role_name_returns_biggest_group_for_largest():
    """Edge case: LARGEST constant maps to 'the biggest group'."""
    assert orders.role_name(orders.LARGEST) == "the biggest group"


def test_role_name_returns_mapped_label_for_known_role():
    """Normal case: a known role returns its label from sim.ROLE_LABEL."""
    expected = sim.ROLE_LABEL.get("foragers", "foragers")
    assert orders.role_name("foragers") == expected


def test_role_name_falls_back_to_input_for_unknown_role():
    """Edge case: an unknown role falls back to the input string itself."""
    assert orders.role_name("unknown_job") == "unknown_job"
