"""Tests for Case.tx_clashes() using real shift data from cases.ALL."""

import cases
import lexicon as lx
from shift import Case


def test_tx_clashes_returns_false_when_treatment_has_no_clash_tag():
    """Normal case: treatment x lacks the clash tag, so no clash is possible regardless of given."""
    for d in cases.ALL:
        c = Case(d)
        non_clash = [i for i, t in enumerate(c.tx) if lx.CLASH_TAG not in lx.TX_BY_ID[t]["tags"]]
        if non_clash:
            assert c.tx_clashes(non_clash[0], 1) is False


def test_tx_clashes_returns_false_when_no_previous_treatment_has_clash_tag():
    """Normal case: treatment x has the clash tag, but no previously given treatments do."""
    for d in cases.ALL:
        c = Case(d)
        clash_ixs = [i for i, t in enumerate(c.tx) if lx.CLASH_TAG in lx.TX_BY_ID[t]["tags"]]
        if len(clash_ixs) >= 1:
            assert c.tx_clashes(clash_ixs[0], 0) is False


def test_tx_clashes_returns_true_when_both_treatments_have_clash_tag():
    """Normal case: treatment x and a previously given treatment both have the clash tag."""
    for d in cases.ALL:
        c = Case(d)
        clash_ixs = [i for i, t in enumerate(c.tx) if lx.CLASH_TAG in lx.TX_BY_ID[t]["tags"]]
        if len(clash_ixs) >= 2:
            assert c.tx_clashes(clash_ixs[1], 1 << clash_ixs[0]) is True


def test_tx_clashes_edge_case_given_is_zero():
    """Edge case: given is 0 (no treatments administered yet), so no clash can occur."""
    for d in cases.ALL:
        c = Case(d)
        clash_ixs = [i for i, t in enumerate(c.tx) if lx.CLASH_TAG in lx.TX_BY_ID[t]["tags"]]
        if clash_ixs:
            assert c.tx_clashes(clash_ixs[0], 0) is False
