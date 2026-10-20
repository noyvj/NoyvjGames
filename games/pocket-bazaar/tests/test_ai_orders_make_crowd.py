from rng import Rng
from orders import make_crowd, Customer


def test_make_crowd_returns_three_customers_with_correct_archetype_and_group():
    """Normal case: verifies structure, archetype, group ID, and family consistency."""
    rng = Rng(42)
    spec = {"max_items": 3, "max_tier": 5, "slack_pct": 300}
    used_names = set()
    group_id = 7

    crowd = make_crowd(rng, spec, ["produce", "textiles", "ceramics"], used_names, group_id)

    assert len(crowd) == 3
    for c in crowd:
        assert isinstance(c, Customer)
        assert c.archetype == "crowd"
        assert c.group == group_id
        families = {item[0] for item in c.items}
        assert len(families) == 1


def test_make_crowd_limits_tiers_to_three_even_when_spec_allows_higher():
    """Normal case: tiers are capped at min(3, spec['max_tier'])."""
    rng = Rng(99)
    spec = {"max_items": 3, "max_tier": 5, "slack_pct": 300}
    used_names = set()

    crowd = make_crowd(rng, spec, ["produce", "textiles", "ceramics"], used_names, group=1)

    for c in crowd:
        for _f, t, _d in c.items:
            assert t <= 3


def test_make_crowd_respects_max_items_cap():
    """Edge case: when spec['max_items'] is small, item count per customer is limited."""
    rng = Rng(123)
    spec = {"max_items": 1, "max_tier": 5, "slack_pct": 300}
    used_names = set()

    crowd = make_crowd(rng, spec, ["produce", "textiles", "ceramics"], used_names, group=2)

    for c in crowd:
        assert len(c.items) == 1


def test_make_crowd_adds_unique_names_to_used_names():
    """Normal case: ensures names are added to the tracking set."""
    rng = Rng(77)
    spec = {"max_items": 3, "max_tier": 5, "slack_pct": 300}
    used_names = {"Tomas", "Ines"}

    make_crowd(rng, spec, ["produce", "textiles", "ceramics"], used_names, group=3)

    assert len(used_names) == 5
