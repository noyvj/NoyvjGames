"""Tests for Hypothesis.sem_of() in deduce.py."""


from deduce import Hypothesis


def _make_hyp():
    """Build a hypothesis using the same format as test_deducibility.py."""
    meanings = (("1000", "LAMPS"), ("1001", "DOOR"), ("1010", "OPEN"), ("1011", "SHUT"), ("1111", "IGNORE"))
    return Hypothesis("binary_msb", meanings)


def test_sem_of_returns_lamps_for_1000():
    """Normal case: known form returns its semantic meaning."""
    hyp = _make_hyp()
    assert hyp.sem_of("1000") == "LAMPS"


def test_sem_of_returns_door_for_1001():
    """Normal case: another known form returns its semantic meaning."""
    hyp = _make_hyp()
    assert hyp.sem_of("1001") == "DOOR"


def test_sem_of_returns_open_for_1010():
    """Normal case: third known form returns its semantic meaning."""
    hyp = _make_hyp()
    assert hyp.sem_of("1010") == "OPEN"


def test_sem_of_returns_ignore_for_unknown_form():
    """Edge case: unknown form defaults to IGNORE."""
    hyp = _make_hyp()
    assert hyp.sem_of("0000") == "IGNORE"
