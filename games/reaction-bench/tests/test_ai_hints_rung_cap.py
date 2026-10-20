"""Test the rung_cap() function in hints.py."""


import hints

# Test normal difficulty returns 3 rungs


def test_rung_cap_normal():
    """Normal difficulty should allow 3 rungs on the hint ladder."""
    assert hints.rung_cap("normal") == 3

# Test hard difficulty returns 2 rungs


def test_rung_cap_hard():
    """Hard difficulty should only allow 2 rungs on the hint ladder."""
    assert hints.rung_cap("hard") == 2

# Test easy difficulty returns 3 rungs (same as normal)


def test_rung_cap_easy():
    """Easy difficulty should allow 3 rungs on the hint ladder."""
    assert hints.rung_cap("easy") == 3

# Test edge case with invalid difficulty


def test_rung_cap_invalid():
    """Invalid difficulty should default to 3 rungs."""
    assert hints.rung_cap("invalid") == 3
