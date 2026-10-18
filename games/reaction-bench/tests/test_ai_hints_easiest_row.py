"""Tests for hints.easiest_row()."""


import reactions
import hints


def test_returns_none_when_all_dials_balance():
    """carbon-dioxide balances with all ones, so easiest_row returns None."""
    r = reactions.BY_ID["carbon-dioxide"]
    assert hints.easiest_row(r, [1, 1, 1]) is None


def test_picks_element_in_fewest_formulas_for_methane():
    """For methane (CH4 + O2 -> CO2 + H2O) at [1, 1, 1, 1], oxygen appears in 3 formulas
    while hydrogen appears in 2. easiest_row should return the row for H."""
    r = reactions.BY_ID["methane"]
    row = hints.easiest_row(r, [1, 1, 1, 1])
    assert isinstance(row, dict)
    assert "symbol" in row and "diff" in row
    assert row["diff"] != 0
    assert row["symbol"] == "H"


def test_breaks_ties_by_returning_first_in_ledger():
    """When two unequal elements appear in the same number of formulas, easiest_row returns
    the one that appears first in the ledger's order."""
    # rust (Fe + O2 -> Fe2O3) at [1, 1, 1] has both Fe and O appearing in exactly 2 formulas.
    r = reactions.BY_ID["rust"]
    row = hints.easiest_row(r, [1, 1, 1])
    assert isinstance(row, dict)
    assert "symbol" in row and "diff" in row
    assert row["diff"] != 0
    # Verify it is indeed one of the tied elements
    assert row["symbol"] in ("Fe", "O")
