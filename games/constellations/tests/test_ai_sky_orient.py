"""Tests for sky.orient(a, b, c) -- the signed area / cross product of vectors ab and ac."""

import sky


def test_left_turn_returns_positive():
    """a=(0,0), b=(1,0), c=(0,1) makes a left (counter-clockwise) turn."""
    assert sky.orient((0, 0), (1, 0), (0, 1)) > 0


def test_right_turn_returns_negative():
    """a=(0,0), b=(1,0), c=(0,-1) makes a right (clockwise) turn."""
    assert sky.orient((0, 0), (1, 0), (0, -1)) < 0


def test_collinear_points_return_zero():
    """a=(0,0), b=(2,2), c=(4,4) are on the same line."""
    assert sky.orient((0, 0), (2, 2), (4, 4)) == 0
