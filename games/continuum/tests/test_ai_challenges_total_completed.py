"""Tests for challenges.total_completed()."""

import types

import challenges


def test_total_completed_returns_zero_for_empty_state():
    state = types.SimpleNamespace(challenge=challenges.empty_state())
    assert challenges.total_completed(state) == 0


def test_total_completed_sums_multiple_challenge_counts():
    state = types.SimpleNamespace(
        challenge={
            "active": None,
            "completed": {"lean_harvest": 2, "land_recovery": 3},
            "failed": 0,
        }
    )
    assert challenges.total_completed(state) == 5


def test_total_completed_handles_zero_and_large_counts():
    state = types.SimpleNamespace(
        challenge={
            "active": None,
            "completed": {"lean_harvest": 0, "land_recovery": 999},
            "failed": 0,
        }
    )
    assert challenges.total_completed(state) == 999
