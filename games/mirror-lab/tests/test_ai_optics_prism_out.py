"""Tests for optics.prism_out(): state 0 splits W into S(left)/L(right), state 1 swaps them; S/L beams only bend."""

import optics


def test_state_0_splits_w_beam_left_and_right():
    # W beam travelling east (d=1): left is north (0), right is south (2)
    assert optics.prism_out(0, "W", 1) == [(0, "S"), (2, "L")]


def test_state_1_swaps_s_and_l_directions():
    # W beam travelling east (d=1): state 1 swaps them, so S goes right (south/2), L goes left (north/0)
    assert optics.prism_out(1, "W", 1) == [(2, "S"), (0, "L")]


def test_s_beam_bends_only_to_its_side():
    # Edge case: S beam entering state 0 prism travelling north (d=0).
    # Left of north is west (3), so it bends west.
    assert optics.prism_out(0, "S", 0) == [(3, "S")]
