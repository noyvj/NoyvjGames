"""Tests for sandbox.clean_era()."""


import sim
import sandbox


def test_valid_era_returns_itself():
    """A known era passes through unchanged."""
    assert sandbox.clean_era("tribal") == "tribal"


def test_another_valid_era_returns_itself():
    """Another known era also passes through unchanged."""
    assert sandbox.clean_era("industrial") == "industrial"


def test_invalid_era_falls_back_to_first_era():
    """An unknown string is replaced by the first era."""
    result = sandbox.clean_era("nonsense")
    assert result == sim.FIRST_ERA
