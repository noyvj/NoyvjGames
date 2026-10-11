"""Every authored case is proved fair: the hidden rule is as short as it can be, the starting examples do not already identify it,
and the stored par test set (with the examples) leaves no other rule of its size or shorter standing."""

import re

import pytest

import cases
import finder
import lang

ALL = cases.ALL_CASES


def test_the_cases_are_assembled_in_drawer_order_with_unique_ids_and_names():
    assert len(ALL) == len(cases.ORDER) == len(cases.BY_ID) >= 8
    assert len({c.name for c in ALL}) == len(ALL)
    for index, drawer in enumerate(cases.DRAWER_LIST):
        assert [c.number for c in drawer["cases"]] == list(range(1, len(drawer["cases"]) + 1))
        assert all(c.drawer == index for c in drawer["cases"])
        assert re.match(r"^[a-z]+$", drawer["id"]) and drawer["name"] and drawer["blurb"]
    for c in ALL:
        assert re.match(r"^[a-z]+(-[a-z]+)*$", c.id) and c.name and c.line


def test_the_first_drawer_is_eight_single_clause_number_gates():
    drawer = cases.DRAWER_LIST[0]
    assert drawer["name"] == "Number Gates" and len(drawer["cases"]) == 8 and drawer["max_clauses"] == 1
    assert all(c.kind == "num" and c.size == 1 and len(c.rule.lits) == 1 for c in drawer["cases"])


@pytest.mark.parametrize("case", ALL, ids=[c.id for c in ALL])
def test_the_hidden_rule_is_exactly_as_short_as_declared(case):
    assert lang.parse_rule(case.kind, case.rule_text) == case.rule and len(case.rule.lits) == case.size
    assert 1 <= case.size <= lang.MAX_CLAUSES <= 3
    assert finder.min_size(case.kind, case.table) == case.size, "a shorter rule has the same table"
    assert case.size <= cases.DRAWER_LIST[case.drawer]["max_clauses"]


@pytest.mark.parametrize("case", ALL, ids=[c.id for c in ALL])
def test_the_examples_are_valid_unique_and_agree_with_the_rule(case):
    dom = case.domain
    assert 1 <= len(case.yes) <= 5 and 1 <= len(case.no) <= 5
    assert len(set(case.examples)) == len(case.examples)
    for key in case.examples:
        assert dom.normalize(key) == key
    assert all(case.accepts(k) for k in case.yes) and not any(case.accepts(k) for k in case.no)


@pytest.mark.parametrize("case", ALL, ids=[c.id for c in ALL])
def test_the_examples_alone_do_not_identify_the_rule_but_the_par_tests_do(case):
    facts = finder.check_par(case.kind, case.rule_text, case.size, case.yes, case.no, case.shortest)
    assert facts["competitors"] > 0, "the examples already identify the rule: there is no game"
    assert facts["sufficient"], "the par tests leave another rule of the same size or shorter standing"
    assert facts["redundant"] == [], "these par tests are not needed: %s" % facts["redundant"]
    assert facts["smaller"] in (None, False), "a smaller par set exists"
    dom = case.domain
    assert len(set(case.shortest)) == len(case.shortest) >= 1
    for key in case.shortest:
        assert dom.normalize(key) == key and key not in case.examples


@pytest.mark.parametrize("case", ALL, ids=[c.id for c in ALL])
def test_par_is_the_shortest_path_plus_the_allowance_and_the_codex_can_show_it(case):
    assert case.par == len(case.shortest) + cases.PAR_ALLOWANCE
    assert cases.medal_for(case, case.par) == "gold" and cases.medal_for(case, case.par + 1) == "silver"
    assert cases.medal_for(case, case.par + cases.SILVER_ALLOWANCE) == "silver" and cases.medal_for(case, case.par + cases.SILVER_ALLOWANCE + 1) == "bronze"
    assert cases.medal_for(case, 0) == "gold"


def test_the_finder_agrees_with_a_brute_force_on_a_small_case():
    """Re-derive the competitor set the slow way (every formula of up to two literals) and compare."""
    dom = lang.domain("num")
    yes, no = ["64", "74"], ["3", "23"]
    ym = sum(1 << dom.index[k] for k in yes)
    nm = sum(1 << dom.index[k] for k in no)
    slow = set()
    lits = [(dom.table(c), c, 0) for c in dom.clause_ids] + [(dom.full ^ dom.table(c), c, 1) for c in dom.clause_ids]
    for ta, _ca, _na in lits:
        for tb, _cb, _nb in lits:
            for t in (ta & tb, ta | tb, ta):
                if t & ym == ym and not t & nm:
                    slow.add(t)
    hidden = lang.rule_table("num", lang.parse_rule("num", "even"))
    slow.discard(hidden)
    assert finder.competitors("num", hidden, 2, yes, no) == slow


def test_the_par_set_finder_is_exact_on_a_hand_made_cover():
    # three competitors whose diffs are {0,1}, {1,2}, {2,3}: two items are enough (1 and 2), one is not
    diffs = [0b0011, 0b0110, 0b1100]
    items, proved = finder.par_set(diffs)
    assert len(items) == 2 and proved and all(any(d >> i & 1 for i in items) for d in diffs)
    items, proved = finder.par_set([0b1000, 0b0001])
    assert items == [0, 3] and proved
    assert finder.par_set([]) == ([], True)


def _drawer(key):
    return [d for d in cases.DRAWER_LIST if d["id"] == key][0]


def test_the_drawers_grow_from_one_clause_to_three_and_each_has_eight_cases():
    assert [d["id"] for d in cases.DRAWER_LIST][:4] == ["numbers", "shapes", "two", "not"]
    assert [d["max_clauses"] for d in cases.DRAWER_LIST][:4] == [1, 1, 2, 3]
    assert all(len(d["cases"]) == 8 for d in cases.DRAWER_LIST)
    assert all(c.kind == "shape" and c.size == 1 for c in _drawer("shapes")["cases"])
    assert all(c.size == 2 and len(c.rule.ops) == 1 for c in _drawer("two")["cases"])
    assert {c.rule.ops[0] for c in _drawer("two")["cases"]} == {"and", "or"}
    assert not any(lang.uses_not(c.rule) for d in cases.DRAWER_LIST[:3] for c in d["cases"])


def test_every_case_in_the_not_drawer_needs_a_not():
    """No rule built only from positive clauses, of the same size or shorter, has the same table."""
    for c in _drawer("not")["cases"]:
        assert lang.uses_not(c.rule), c.id
        lits = [c2 for c2 in c.domain.clause_ids]
        tables = [c.domain.table(x) for x in lits]
        found = set(tables)
        level = set(tables)
        for _n in range(c.size - 1):
            level = {a & b for a in level for b in tables} | {a | b for a in level for b in tables}
            found |= level
        assert c.table not in found, "%s can be written without a not" % c.id


def test_the_drawers_use_every_family_of_clause_at_least_once_across_the_game():
    used = {f for c in cases.ALL_CASES for f in c.families}
    assert len(used) >= 14
