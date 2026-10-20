"""Tests for consulting.inherited_for()."""

import consulting
import save


def _fresh(case="smokestack"):
    c = save.Campaign()
    assert consulting.apply(c, case)
    return c


def test_inherited_for_returns_valid_nodes_for_smokestack_case():
    """Smokestack is an industrial-era case; inherited nodes should be valid tier-1/2 nodes."""
    c = _fresh("smokestack")
    nodes = consulting.inherited_for(c)
    assert isinstance(nodes, list) and len(nodes) > 0
    for nid in nodes:
        assert nid in c.tree.nodes


def test_inherited_for_returns_valid_nodes_for_sprawl_case():
    """Sprawl is a digital-era case; inherited nodes should be valid tier-1/2/3 nodes."""
    c = _fresh("sprawl")
    nodes = consulting.inherited_for(c)
    assert isinstance(nodes, list) and len(nodes) > 0
    for nid in nodes:
        assert nid in c.tree.nodes


def test_inherited_for_returns_empty_list_when_no_case_active():
    """Without an active consulting case, inherited_for should return an empty list."""
    c = save.Campaign()
    assert consulting.get(c.ui) is None
    nodes = consulting.inherited_for(c)
    assert nodes == []
