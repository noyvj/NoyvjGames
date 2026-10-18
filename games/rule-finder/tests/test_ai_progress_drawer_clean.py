"""Tests for progress.drawer_clean()."""

import cases
import progress


def test_drawer_clean_counts_cases_within_par():
    """drawer_clean() counts only named cases whose test count is <= par."""
    drawer = cases.DRAWER_LIST[0]
    c1, c2 = drawer["cases"][0], drawer["cases"][1]

    named = {
        c1.id: {"t": c1.par, "r": "even"},  # exactly par -> clean
        c2.id: {"t": c2.par + 5, "r": "odd"},  # over par -> not clean
    }
    assert progress.drawer_clean(named, drawer) == 1


def test_drawer_clean_all_clean():
    """drawer_clean() returns the total number of cases when all are named and clean."""
    drawer = cases.DRAWER_LIST[0]
    named = {c.id: {"t": c.par, "r": "even"} for c in drawer["cases"]}
    assert progress.drawer_clean(named, drawer) == len(drawer["cases"])


def test_drawer_clean_edge_empty_named():
    """drawer_clean() returns 0 when no cases are named."""
    drawer = cases.DRAWER_LIST[0]
    named = {}
    assert progress.drawer_clean(named, drawer) == 0
