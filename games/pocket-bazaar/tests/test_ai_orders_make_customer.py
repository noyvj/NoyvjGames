import pytest

import days
from orders import make_customer, Customer
from rng import Rng

THREE = ["produce", "textiles", "ceramics"]


def test_regular_customer_structure():
    """A regular customer gets items within the day's max_items and max_tier limits."""
    spec = days.spec(10)
    for seed in range(20):
        used_names = set()
        cust = make_customer(Rng(seed * 7 + 1), spec, THREE, used_names)
        assert isinstance(cust, Customer)
        assert 1 <= len(cust.items) <= spec["max_items"]
        assert all(f in THREE for f, t, _ in cust.items)
        assert all(1 <= t <= spec["max_tier"] for _, t, _ in cust.items)


def test_haggler_critic_item_limit():
    """Hagglers and Critics never receive more than two items."""
    spec = days.spec(10)
    for seed in range(50):
        used_names = set()
        rng = Rng(seed * 11 + 2)
        cust = make_customer(rng, spec, THREE, used_names)
        if cust.archetype in ("haggler", "critic"):
            assert len(cust.items) <= 2
            break
    else:
        pytest.fail("Could not generate a haggler or critic in 50 tries")


def test_child_customer_single_item():
    """A child customer always receives exactly one item of tier 1 or 2."""
    spec = days.spec(10)
    # "child" is unlocked by renown; skip if not available on this day.
    archetypes = dict(spec["archetypes"]) if isinstance(spec["archetypes"], list) else spec["archetypes"]
    if "child" not in archetypes:
        pytest.skip("Child archetype not available on this day")
    used_names = set()
    # "child" may be rare on day 10; try many seeds to find one.
    for seed in range(5000):
        rng = Rng(seed * 13 + 3)
        cust = make_customer(rng, spec, THREE, used_names)
        if cust.archetype == "child":
            assert len(cust.items) == 1
            _, tier, _ = cust.items[0]
            assert 1 <= tier <= min(2, spec["max_tier"])
            break
    else:
        pytest.fail("Could not generate a child customer in 5000 tries")
