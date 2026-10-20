"""Edge-case tests for codex.py."""

import cases
import codex


def test_filled_empty_named():
    """filled() returns False when named is empty."""
    assert codex.filled({}, "latch") is False


def test_filled_single_match():
    """filled() returns True when the case id is in named."""
    named = {"latch": {"t": 0, "r": "even"}}
    assert codex.filled(named, "latch") is True


def test_filled_multiple_keys():
    """filled() correctly checks membership among multiple keys."""
    named = {"latch": {}, "hinge": {}}
    assert codex.filled(named, "hinge") is True
    assert codex.filled(named, "missing") is False


def test_summary_empty_inputs():
    """summary() returns entries with filled=False and read=False when inputs are empty."""
    summary = codex.summary({}, set())
    assert len(summary) > 0
    for entry in summary:
        assert entry["filled"] is False
        assert entry["read"] is False


def test_summary_all_filled_and_read():
    """summary() marks all cases as filled and read when inputs cover everything."""
    named = {c.id: {"t": 0, "r": "even"} for d in cases.DRAWER_LIST for c in d["cases"]}
    read = set(named.keys())
    summary = codex.summary(named, read)
    for entry in summary:
        assert entry["filled"] is True
        assert entry["read"] is True


def test_page_returns_none_when_not_named():
    """page() returns None when the case is not in named."""
    case = cases.DRAWER_LIST[0]["cases"][0]
    result = codex.page(case, {}, set())
    assert result is None


def test_page_returns_dict_when_named():
    """page() returns a dict with expected keys when the case is named."""
    case = cases.DRAWER_LIST[0]["cases"][0]
    named = {case.id: {"t": 1, "r": "even"}}
    read = set()
    result = codex.page(case, named, read)
    assert isinstance(result, dict)
    assert result["id"] == case.id
    assert result["read"] is False


def test_counts_empty_inputs():
    """counts() returns zeros for filled and read when inputs are empty."""
    res = codex.counts({}, set())
    assert res["filled"] == 0
    assert res["read"] == 0
    assert res["total"] > 0


def test_counts_full_inputs():
    """counts() correctly tallies filled and read when all cases are processed."""
    named = {c.id: {"t": 0, "r": "even"} for d in cases.DRAWER_LIST for c in d["cases"]}
    read = set(named.keys())
    res = codex.counts(named, read)
    assert res["filled"] == len(named)
    assert res["read"] == len(read)
    assert res["total"] > 0
