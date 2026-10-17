"""Tests for gen.data_for(): retrieves case data by share code or practice id."""

import gen


def test_data_for_returns_case_data_for_a_share_code():
    """A valid share code yields the expected case data structure."""
    code = gen.code_of(1, 0)
    data = gen.data_for(code)
    assert data is not None
    assert data["id"] == gen.case_id(1, 0)
    assert data["layout"] in ("cottage", "lodge", "bungalow", "flat")
    assert isinstance(data["truth"], tuple) and len(data["truth"]) >= 1


def test_data_for_returns_case_data_for_a_practice_id():
    """A valid practice id yields the exact same case data as its share code."""
    cid = gen.case_id(1, 0)
    code = gen.code_of(1, 0)
    data_from_id = gen.data_for(cid)
    data_from_code = gen.data_for(code)
    assert data_from_id is not None
    assert data_from_id == data_from_code


def test_data_for_returns_none_for_invalid_inputs():
    """Invalid inputs (wrong format, non-string, out-of-range seed) return None."""
    for bad in (None, 123, "", "EH9-0", "practice-9-0", "EVIDENCEHUNT-K7F2Q"):
        assert gen.data_for(bad) is None, f"Expected None for {bad!r}"
