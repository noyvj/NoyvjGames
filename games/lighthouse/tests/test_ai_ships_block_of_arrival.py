"""Tests for the block_of_arrival() function in ships.py."""

import ships
from clock import night_len


def test_block_returns_zero_one_or_two():
    """block_of_arrival always returns 0, 1, or 2 regardless of seed or night."""
    for seed in range(1, 6):
        for night in range(1, 41):
            ship_list = ships.ships_for_night(seed, night, False)
            for s in ship_list:
                block = ships.block_of_arrival(night, s)
                assert 0 <= block <= 2


def test_early_ships_get_block_zero():
    """Ships arriving early enough fall into block 0."""
    for seed in range(1, 6):
        for night in range(1, 41):
            ship_list = ships.ships_for_night(seed, night, False)
            length = night_len(night)
            for s in ship_list:
                if s["arrive"] * 3 < length:
                    assert ships.block_of_arrival(night, s) == 0


def test_late_ships_get_block_two():
    """Ships arriving late enough fall into block 2."""
    for seed in range(1, 6):
        for night in range(1, 41):
            ship_list = ships.ships_for_night(seed, night, False)
            length = night_len(night)
            for s in ship_list:
                if s["arrive"] * 3 >= 2 * length:
                    assert ships.block_of_arrival(night, s) == 2


def test_edge_case_minimum_arrival():
    """A ship arriving at the minimum possible tick maps correctly."""
    seed = 1
    night = 1
    ship_list = ships.ships_for_night(seed, night, False)
    if ship_list:
        s = ship_list[0]
        length = night_len(night)
        expected = min(2, s["arrive"] * 3 // length)
        assert ships.block_of_arrival(night, s) == expected
