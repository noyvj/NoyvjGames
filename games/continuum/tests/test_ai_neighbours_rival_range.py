"""Tests for neighbours.rival_range()."""

import neighbours


def test_rival_range_returns_correct_bounds_for_era_0():
    record = neighbours.default()
    low, high = neighbours.rival_range(record, 10, 0)
    assert low == 1 and high == 10


def test_rival_range_scales_with_player_era():
    record = neighbours.default()
    low_1, high_1 = neighbours.rival_range(record, 10, 1)
    low_2, high_2 = neighbours.rival_range(record, 10, 5)
    assert low_1 < low_2 and high_1 < high_2
    assert low_1 == 3 and high_1 == 12
    assert low_2 == 11 and high_2 == 20


def test_rival_range_lower_bound_clamps_to_one_for_negative_era():
    record = neighbours.default()
    low, high = neighbours.rival_range(record, 10, -5)
    assert low == 1 and high == 10


def test_rival_range_ignores_record_and_season():
    record_a = neighbours.default()
    record_b = {
        "seed": 99,
        "slots": {sid: {"attitude": -3} for sid in neighbours.SLOT_IDS},
        "lease": {"holder": "n1", "until": 100, "pending": 50, "auctions": 10},
        "events": [],
    }
    low_a, high_a = neighbours.rival_range(record_a, 1, 5)
    low_b, high_b = neighbours.rival_range(record_b, 9999, 5)
    assert (low_a, high_a) == (low_b, high_b)
