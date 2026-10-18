"""Tests for lang.make_rule()."""

import lang


def test_make_rule_with_two_clauses_and_one_operator():
    lits = [("even", 0), ("ge:50", 1)]
    ops = ("and",)
    rule = lang.make_rule(lits, ops)
    assert isinstance(rule, lang.Rule)
    assert rule.lits == (("even", 0), ("ge:50", 1))
    assert rule.ops == ("and",)


def test_make_rule_with_three_clauses_and_two_operators():
    lits = [("prime", 0), ("square", 1), ("has:7", 0)]
    ops = ("or", "and")
    rule = lang.make_rule(lits, ops)
    assert isinstance(rule, lang.Rule)
    assert rule.lits == (("prime", 0), ("square", 1), ("has:7", 0))
    assert rule.ops == ("or", "and")


def test_make_rule_with_one_clause_and_empty_ops():
    lits = [("even", 1)]
    ops = ()
    rule = lang.make_rule(lits, ops)
    assert isinstance(rule, lang.Rule)
    assert rule.lits == (("even", 1),)
    assert rule.ops == ()


def test_make_rule_normalizes_boolean_negation_to_int():
    lits = [("prime", True), ("square", False)]
    ops = ("and",)
    rule = lang.make_rule(lits, ops)
    assert rule.lits == (("prime", 1), ("square", 0))
