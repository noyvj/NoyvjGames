"""Tests for consulting.inherited_nodes()."""

from collections import Counter

import consulting
import research
import save


def test_inherited_nodes_returns_valid_node_ids_for_industrial():
    """Normal case: inherited nodes for an industrial-era case are valid."""
    c = save.Campaign()
    consulting.apply(c, "smokestack")
    nodes = consulting.inherited_nodes(c.tree, "industrial")

    assert isinstance(nodes, list)
    first_tier = research.era_tiers("industrial")[0]
    for node_id in nodes:
        node = c.tree.nodes[node_id]
        assert node.tier < first_tier
        assert not node.min_affinity


def test_inherited_nodes_respects_tier_unlock_requirement():
    """Normal case: picks at most TIER_UNLOCK_REQUIREMENT per tier."""
    c = save.Campaign()
    consulting.apply(c, "smokestack")
    nodes = consulting.inherited_nodes(c.tree, "industrial")

    tier_counts = Counter(n.tier for n in (c.tree.nodes[nid] for nid in nodes))
    for tier, count in tier_counts.items():
        assert count <= research.TIER_UNLOCK_REQUIREMENT


def test_inherited_nodes_returns_empty_for_early_era():
    """Edge case: an era starting at tier 1 yields no inherited nodes."""
    c = save.Campaign()
    # Tribal starts at tier 1, so range(1, 1) is empty.
    nodes = consulting.inherited_nodes(c.tree, "tribal")
    assert nodes == []
