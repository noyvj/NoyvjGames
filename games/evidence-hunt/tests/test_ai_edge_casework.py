"""Edge-case tests for casework.py."""


import casework as cw
import progress


def test_grade_of_limits():
    """grade_of returns 3 for cost 0, 2 for cost <= 2, 1 otherwise."""
    assert cw.grade_of(0) == 3
    assert cw.grade_of(1) == 2
    assert cw.grade_of(2) == 2
    assert cw.grade_of(3) == 1
    assert cw.grade_of(4) == 1


def test_grade_for_difficulties():
    """grade_for adjusts seal thresholds per difficulty."""
    # Easy: clean <= 1, steady <= 3
    assert cw.grade_for(0, "easy") == 3
    assert cw.grade_for(1, "easy") == 3
    assert cw.grade_for(2, "easy") == 2
    assert cw.grade_for(3, "easy") == 2
    assert cw.grade_for(4, "easy") == 1
    # Hard: clean <= 0, steady <= 1
    assert cw.grade_for(0, "hard") == 3
    assert cw.grade_for(1, "hard") == 2
    assert cw.grade_for(2, "hard") == 1
    # Normal (default)
    assert cw.grade_for(0, "normal") == 3
    assert cw.grade_for(2, "normal") == 2
    assert cw.grade_for(3, "normal") == 1


def test_popcount_limits():
    """popcount handles zero and typical bitmask sizes correctly."""
    assert cw.popcount(0) == 0
    assert cw.popcount(1) == 1
    assert cw.popcount((1 << 6) - 1) == 6  # max kit size
    assert cw.popcount(255) == 8


def test_to_token_and_from_token_edge_cases():
    """to_token and from_token handle valid, invalid, and boundary inputs."""
    # Valid pack action
    token = cw.to_token(("pack", 0))
    assert cw.from_token(token) == ("pack", 0)

    # Invalid: wrong number of parts for 'van'
    assert cw.from_token("van:1") is None

    # Invalid: negative numbers
    assert cw.from_token("pack:-1") is None

    # Invalid: numbers > 99
    assert cw.from_token("pack:100") is None

    # Empty or non-string
    assert cw.from_token("") is None
    assert cw.from_token(123) is None


def test_case_apply_invalid_inputs():
    """Case.apply rejects out-of-bounds equipment and room indices."""
    case = cw.Case(progress.DATA["1-1"])
    st = case.new_state()

    # Invalid equipment index (negative)
    st2, info = case.apply(st, ("pack", -1))
    assert st2 is None and info["kind"] == "refused"

    # Invalid equipment index (too large)
    st2, info = case.apply(st, ("pack", 6))
    assert st2 is None and info["kind"] == "refused"

    # Invalid room index (negative)
    st2, info = case.apply(st, ("go", -1))
    assert st2 is None and info["kind"] == "refused"

    # Invalid room index (too large)
    num_rooms = len(case.rooms)
    st2, info = case.apply(st, ("go", num_rooms))
    assert st2 is None and info["kind"] == "refused"
