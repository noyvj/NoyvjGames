"""Tests for neighbour_era() in neighbours.py."""


import neighbours
import sim


def test_neighbour_era_advances_with_season():
    # n1 has offset=15, pace=55. Season 55 -> (55+15)//55 = 1
    assert neighbours.neighbour_era(42, "n1", 55) == 1
    # n2 has offset=0, pace=70. Season 70 -> (70+0)//70 = 1
    assert neighbours.neighbour_era(42, "n2", 70) == 1


def test_neighbour_era_starts_at_era_index_0():
    # n3 has offset=40, pace=90. Season 1 -> (1+40)//90 = 0
    assert neighbours.neighbour_era(42, "n3", 1) == 0


def test_neighbour_era_clamps_to_the_last_era_index():
    # A very large season should not exceed the maximum era index.
    max_idx = len(sim.ERA_ORDER) - 1
    assert neighbours.neighbour_era(42, "n1", 10**7) == max_idx


def test_neighbour_era_treats_season_zero_as_one():
    # The function uses max(1, season), so season=0 behaves like season=1.
    val_at_0 = neighbours.neighbour_era(42, "n2", 0)
    val_at_1 = neighbours.neighbour_era(42, "n2", 1)
    assert val_at_0 == val_at_1
