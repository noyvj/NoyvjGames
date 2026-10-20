"""Tests for ResearchTree.researched_nodes()."""

import research


def test_researched_nodes_returns_empty_on_new_tree():
    tree = research.build_tree()
    assert tree.researched_nodes() == []


def test_researched_nodes_includes_researched_ids():
    tree = research.build_tree()
    node_id = "foraging_lore"
    resources = {"knowledge": 100}
    tree.research(node_id, resources)
    assert {n.node_id for n in tree.researched_nodes()} == {node_id}


def test_researched_nodes_handles_multiple_researches():
    tree = research.build_tree()
    node_ids = ["foraging_lore", "early_agriculture"]
    resources = {"knowledge": 100}
    researched = []
    for nid in node_ids:
        if nid in tree.nodes:
            tree.research(nid, resources)
            researched.append(nid)
    assert {n.node_id for n in tree.researched_nodes()} == set(researched)


def test_researched_nodes_does_not_duplicate_on_repeat_research():
    tree = research.build_tree()
    node_id = "foraging_lore"
    resources = {"knowledge": 100}
    tree.research(node_id, resources)
    tree.research(node_id, resources)
    assert sum(1 for n in tree.researched_nodes() if n.node_id == node_id) == 1
