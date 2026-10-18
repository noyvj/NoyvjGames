"""Tests for floors_of() in houses.py."""

import houses


def test_floors_of_schoolhouse_returns_descending_order():
    rooms = houses.rooms_of("schoolhouse")
    assert houses.floors_of(rooms) == [1, 0, -1]


def test_floors_of_inn_returns_all_four_floors_descending():
    rooms = houses.rooms_of("inn")
    assert houses.floors_of(rooms) == [2, 1, 0, -1]


def test_floors_of_single_floor_layout_returns_singleton_list():
    rooms = houses.rooms_of("cottage")
    assert houses.floors_of(rooms) == [0]
