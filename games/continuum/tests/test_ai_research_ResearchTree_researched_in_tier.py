"""Tests for ResearchTree.researched_in_tier()."""


import research


def test_returns_zero_when_no_nodes_researched():
    tree = research.build_tree()
    tiers_present = {n.tier for n in tree.nodes.values()}
    sample_tier = min(tiers_present)
    assert tree.researched_in_tier(sample_tier) == 0


def test_increments_count_as_nodes_are_researched():
    tree = research.build_tree()
    available_node = next(n for n in tree.nodes.values() if tree.is_available(n.node_id))
    tier = available_node.tier

    assert tree.researched_in_tier(tier) == 0

    resources = {"knowledge": available_node.cost}
    tree.research(available_node.node_id, resources)

    assert tree.researched_in_tier(tier) == 1


def test_handles_nonexistent_tiers_gracefully():
    tree = research.build_tree()
    max_tier = max(n.tier for n in tree.nodes.values()) + 10
    assert tree.researched_in_tier(max_tier) == 0
