"""Edge-case tests for chem.py."""

import pytest
import chem


def test_count_atoms_handles_empty_and_invalid_inputs():
    """Test count_atoms with empty string, invalid characters, and single element."""
    with pytest.raises(chem.FormulaError):
        chem.count_atoms("")
    with pytest.raises(chem.FormulaError):
        chem.count_atoms("H2O!")
    assert chem.count_atoms("H") == {"H": 1}


def test_solutions_respects_limit_and_finds_nothing_when_impossible():
    """Test solutions with limit=1, limit=MAX_COEF, and impossible reactions."""
    assert chem.solutions(["H2", "O2"], ["H2O"], limit=1) == []
    assert [2, 1, 2] in chem.solutions(["H2", "O2"], ["H2O"], limit=12)
    assert chem.solutions(["H2"], ["NaCl"], limit=50) == []


def test_smallest_returns_none_when_no_valid_solution_exists():
    """Test smallest returns None when coefficients exceed dial range or reaction is impossible."""
    assert chem.smallest(["C8H18", "O2"], ["CO2", "H2O"]) is None
    assert chem.smallest(["H2"], ["NaCl"]) is None


def test_is_balanced_handles_edge_cases():
    """Test is_balanced with empty list, non-zero diff, and balanced rows."""
    assert not chem.is_balanced([])
    rows = [{"symbol": "H", "left": 2, "right": 3, "diff": -1}]
    assert not chem.is_balanced(rows)
    rows = [{"symbol": "H", "left": 2, "right": 2, "diff": 0}]
    assert chem.is_balanced(rows)


def test_lint_handles_empty_and_boundary_inputs():
    """Test lint with empty inputs, empty strings, and banned words at various positions."""
    assert chem.lint([], []) == []
    problems = chem.lint([""], [""])
    assert len(problems) == 1 and "empty formula" in problems[0]
    assert len(chem.lint(["bomb here"], ["H2O"])) > 0
    assert len(chem.lint(["make a bomb"], ["H2O"])) > 0
    assert len(chem.lint(["do not explode"], ["H2O"])) > 0
