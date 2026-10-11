"""Milestone 1: the formula parser, the ledger, the exact balancer and the banned-list lint."""

import pytest

import chem
import elements


def test_the_parser_counts_atoms_including_brackets_and_repeats():
    assert chem.count_atoms("H2O") == {"H": 2, "O": 1}
    assert chem.count_atoms("Ca(OH)2") == {"Ca": 1, "O": 2, "H": 2}
    assert chem.count_atoms("(NH4)2SO4") == {"N": 2, "H": 8, "S": 1, "O": 4}
    assert chem.count_atoms("C2H5OH") == {"C": 2, "H": 6, "O": 1}          # H appears twice and is added up
    assert chem.count_atoms("Al2(SO4)3") == {"Al": 2, "S": 3, "O": 12}
    assert chem.count_atoms("Fe") == {"Fe": 1}
    assert chem.count_atoms("Mg3(PO4)2(OH)")["O"] == 9                      # more than one group in a formula
    assert chem.count_atoms("Ca(OH(H2O)2)2") == {"Ca": 1, "O": 6, "H": 10}  # a group inside a group


def test_the_parser_gives_the_structure_the_page_draws():
    tree = chem.parse_tree("Ca(OH)2")
    assert tree[0] == {"t": "el", "sym": "Ca", "n": 1}
    assert tree[1]["t"] == "group" and tree[1]["n"] == 2
    assert [p["sym"] for p in tree[1]["parts"]] == ["O", "H"]
    assert chem.has_group("Ca(OH)2") and not chem.has_group("CaCO3")


@pytest.mark.parametrize("bad", ["", "h2o", "H2(", "H2)", "()", "(H)0", "2H", "H0", "H2O!", "(", " ", "Ca(OH)2)", None, 7])
def test_unreadable_formulas_are_refused(bad):
    with pytest.raises(chem.FormulaError):
        chem.count_atoms(bad)


def test_the_ledger_counts_both_sides_and_the_difference_is_right_minus_left():
    rows = chem.ledger(["H2", "O2"], ["H2O"], [1, 1, 1])
    assert rows == [{"symbol": "H", "left": 2, "right": 2, "diff": 0}, {"symbol": "O", "left": 2, "right": 1, "diff": -1}]
    assert not chem.is_balanced(rows)
    rows = chem.ledger(["H2", "O2"], ["H2O"], [2, 1, 2])
    assert chem.is_balanced(rows) and all(r["diff"] == 0 for r in rows)
    rows = chem.ledger(["H2", "O2"], ["H2O"], [3, 1, 2])
    assert rows[0]["diff"] == -2 and rows[1]["diff"] == 0
    rows = chem.ledger(["H2", "O2"], ["H2O"], [1, 1, 3])
    assert rows[0]["diff"] == 4 and rows[1]["diff"] == 1


def test_the_ledger_lists_elements_in_order_of_first_appearance():
    assert [r["symbol"] for r in chem.ledger(["CH4", "O2"], ["CO2", "H2O"], [1, 2, 1, 2])] == ["C", "H", "O"]
    assert chem.elements_of(["NH3", "H2SO4"]) == ["N", "H", "S", "O"]


def test_an_empty_side_is_never_balanced():
    assert not chem.is_balanced([])


def test_the_exact_balancer_finds_the_textbook_answers():
    assert chem.smallest(["H2", "O2"], ["H2O"]) == [2, 1, 2]
    assert chem.smallest(["Fe", "O2"], ["Fe2O3"]) == [4, 3, 2]
    assert chem.smallest(["C3H8", "O2"], ["CO2", "H2O"]) == [1, 5, 3, 4]
    assert chem.smallest(["NH3", "O2"], ["N2", "H2O"]) == [4, 3, 2, 6]
    assert chem.smallest(["Fe(OH)2", "O2", "H2O"], ["Fe(OH)3"]) == [4, 1, 2, 4]
    assert chem.smallest(["C6H12O6", "O2"], ["CO2", "H2O"]) == [1, 6, 6, 6]


def test_the_nullspace_has_the_right_dimension():
    assert len(chem.nullspace(["H2", "O2"], ["H2O"])) == 1
    assert len(chem.nullspace(["H2", "O2"], ["H2O", "H2O2"])) == 2        # two independent ways to balance
    assert len(chem.nullspace(["H2"], ["NaCl"])) == 0                      # nothing can balance it
    for v in chem.nullspace(["H2", "O2"], ["H2O", "H2O2"]):
        assert len(v) == 4


def test_a_set_that_cannot_be_balanced_has_no_solution_and_says_why():
    assert not chem.can_balance(["CH4", "O2"], ["CO2"])
    assert not chem.can_balance(["CH4", "O2"], ["CO2", "NaCl"])
    assert not chem.can_balance(["NaHCO3"], ["Na2CO3", "H2O"])             # every element is on both sides, still impossible
    assert "nowhere" in chem.why_not(["CH4", "O2"], ["CO2", "NaCl"]) or "appear" in chem.why_not(["CH4", "O2"], ["CO2", "NaCl"])
    assert "Sodium" in chem.why_not(["CH4", "O2"], ["CO2", "NaCl"])
    assert "Hydrogen" in chem.why_not(["CH4", "O2"], ["CO2"])
    assert "no whole-number" in chem.why_not(["NaHCO3"], ["Na2CO3", "H2O"])


def test_coefficients_above_the_dial_range_do_not_count():
    # 2 C8H18 + 25 O2 -> 16 CO2 + 18 H2O needs 25, beyond the 12 on the dials
    assert chem.solutions(["C8H18", "O2"], ["CO2", "H2O"]) == []
    assert chem.solutions(["C8H18", "O2"], ["CO2", "H2O"], limit=30) == [[2, 25, 16, 18]]


def test_a_non_minimal_setting_balances_but_is_not_lowest_terms():
    rows = chem.ledger(["H2", "O2"], ["H2O"], [4, 2, 4])
    assert chem.is_balanced(rows) and not chem.lowest_terms([4, 2, 4]) and chem.lowest_terms([2, 1, 2])


def test_mass_is_exact_and_equal_on_both_sides_for_a_balanced_setting():
    masses = {"H": "1.0080", "O": "15.999"}
    assert chem.formula_mass("H2O", masses) == chem.Fraction("18.015")
    assert chem.side_mass(["H2", "O2"], [2, 1], masses) == chem.side_mass(["H2O"], [2], masses)
    assert chem.side_mass(["H2", "O2"], [1, 1], masses) != chem.side_mass(["H2O"], [1], masses)


def test_the_banned_list_lint_catches_words_and_formulas():
    assert chem.lint(["Water is wet."], ["H2O"]) == []
    assert chem.lint(["how to make a bomb"], ["H2O"])
    assert chem.lint(["a sarin story"], ["H2O"])
    assert chem.lint(["fine"], ["KClO3"]) and chem.lint(["fine"], ["ClO3K"])        # same atoms in another order are still caught
    assert chem.lint(["fine"], ["NH4NO3"]) and chem.lint(["fine"], ["HCN"]) and chem.lint(["fine"], ["CO"])
    assert chem.lint(["fine"], ["Q9"])                                              # unreadable formulas are problems too
    assert chem.lint(["methane burns"], ["CH4"]) == []                             # the word 'meth...' alone is not banned
