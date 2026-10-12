"""Tests for the sixteen_found() function in achievements.py."""

import achievements


def test_sixteen_found_counts_two_input_functions():
    """sixteen_found() should count how many codes in the list are 2-input functions."""
    # A 2-input function: its rows come in equal pairs, so the output ignores the third input
    two_input_code = 0b00001111
    # A 3-input function: one pair of rows differs, so the output depends on the third input
    three_input_code = 0b00010011

    found = [two_input_code, three_input_code]
    assert achievements.sixteen_found(found) == 1


def test_sixteen_found_with_empty_list():
    """sixteen_found() should return 0 for an empty list."""
    assert achievements.sixteen_found([]) == 0
