"""Tests for solver.all_kits()."""

import casework as cw
import progress
import solver


def test_all_kits_returns_smallest_first():
    """Kits should be returned sorted by size, then lexicographically."""
    case = cw.Case(progress.DATA["1-1"])
    kits = solver.all_kits(case)
    sizes = [len(k) for k in kits]
    assert sizes == sorted(sizes), "Kits must be ordered smallest first"


def test_all_kits_separates_candidates():
    """Every returned kit must separate candidates for every slot."""
    for cid in ("1-1", "2-1", "3-1"):
        case = cw.Case(progress.DATA[cid])
        kits = solver.all_kits(case)
        for s in range(case.n):
            for kit in kits:
                assert solver.separates(case, set(kit), s), f"Case {cid}: Kit {kit} fails to separate slot {s}"


def test_all_kits_respects_limit():
    """Passing a limit smaller than the case's kit size should only return kits up to that size."""
    case = cw.Case(progress.DATA["1-1"])  # kit_size is 3
    limited_kits = solver.all_kits(case, limit=1)
    assert all(len(k) <= 1 for k in limited_kits), "Kits must not exceed the given limit"
    assert len(limited_kits) > 0, "A fair case should yield at least one valid kit within its min_kit"


def test_all_kits_edge_case_limit_zero():
    """When limit is 0, no equipment can be packed, so it returns an empty list."""
    case = cw.Case(progress.DATA["1-1"])
    assert solver.all_kits(case, limit=0) == [], "limit=0 should yield no kits"
