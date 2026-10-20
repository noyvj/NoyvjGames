"""Edge cases for casekit.py helpers."""

from casekit import P, S


def test_P_accepts_empty_strings():
    """P should store empty strings without error when provided."""
    p = P("", "", "")
    assert p["crew"] == ""
    assert p["truth"] == ""
    assert p["say"] == ""
    assert p["traits"] == ""


def test_P_accepts_list_truth():
    """P should accept a list of conditions for the truth field."""
    p = P("crew1", ["cond_a", "cond_b"], "says hi")
    assert p["truth"] == ["cond_a", "cond_b"]


def test_S_defaults_are_correct():
    """S should use correct defaults for optional shift parameters."""
    s = S("s1", "Title", "Intro", "pool", {"gel": 1}, [P("c", "t", "s")])
    assert s["tests"] == ""
    assert s["beds"] == 0
    assert s["robots"] == 0
    assert s["maxc"] == 1


def test_S_accepts_zero_beds_and_robots():
    """S should accept zero for beds and robots explicitly."""
    s = S("s2", "T", "I", "p", {"gel": 1}, [P("c", "t", "s")], beds=0, robots=0)
    assert s["beds"] == 0
    assert s["robots"] == 0


def test_S_accepts_large_maxc():
    """S should accept a large maxc value without clamping or error."""
    s = S("s3", "T", "I", "p", {"gel": 1}, [P("c", "t", "s")], maxc=99)
    assert s["maxc"] == 99


def test_S_accepts_empty_stock_and_pool():
    """S should accept empty dict for stock and empty string for pool."""
    s = S("s4", "T", "I", "", {}, [P("c", "t", "s")])
    assert s["stock"] == {}
    assert s["pool"] == ""
