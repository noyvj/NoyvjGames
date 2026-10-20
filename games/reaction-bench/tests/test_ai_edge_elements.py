"""Edge-case tests for elements.py."""


import elements


def test_position_at_smallest_and_largest_values():
    assert elements.position(1) == (1, 1, "body")
    assert elements.position(118) == (7, 18, "body")


def test_position_across_the_lanthanide_gap():
    assert elements.position(56) == (6, 2, "body")
    assert elements.position(57) == (9, 3, "f")
    assert elements.position(71) == (9, 17, "f")
    assert elements.position(72) == (6, 4, "body")


def test_position_across_the_actinide_gap():
    assert elements.position(88) == (7, 2, "body")
    assert elements.position(89) == (10, 3, "f")
    assert elements.position(103) == (10, 17, "f")
    assert elements.position(104) == (7, 4, "body")


def test_period_of_f_block_elements():
    assert elements.period_of(57) == 6
    assert elements.period_of(71) == 6
    assert elements.period_of(89) == 7
    assert elements.period_of(103) == 7


def test_group_of_f_block_elements():
    assert elements.group_of(57) == 0
    assert elements.group_of(71) == 0
    assert elements.group_of(89) == 0
    assert elements.group_of(103) == 0


def test_name_and_number_for_a_known_element():
    assert elements.name_of("H") == "hydrogen"
    assert elements.number_of("H") == 1
