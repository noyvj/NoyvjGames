"""Edge-case tests for decision.py."""

import pytest
import decision
from setdata import load_set_dict


@pytest.fixture
def sample(raw):
    return load_set_dict(raw)


def test_option_order_returns_all_options_for_a_valid_decision(sample):
    """Valid decision ID returns a list containing every option ID exactly once."""
    order = decision.option_order(sample, "d-sumter")
    assert isinstance(order, list)
    assert len(order) == 3
    assert set(order) == {"reinforce", "supply", "withdraw"}


def test_option_order_raises_for_unknown_decision_id(sample):
    """Unknown decision ID raises ValueError with a clear message."""
    with pytest.raises(ValueError, match="unknown decision"):
        decision.option_order(sample, "nonexistent")


def test_option_order_is_deterministic_across_calls(sample):
    """Calling option_order twice on the same inputs yields identical orderings."""
    order1 = decision.option_order(sample, "d-sumter")
    order2 = decision.option_order(sample, "d-sumter")
    assert order1 == order2


def test_seed_version_is_non_empty_string():
    """SEED_VERSION is a non-empty string used for puzzle pinning."""
    assert isinstance(decision.SEED_VERSION, str) and len(decision.SEED_VERSION) > 0


def test_parts_contains_required_claim_keys():
    """PARTS lists the three claim parts that must exist for every decision."""
    assert decision.PARTS == ("options", "choice", "after")
