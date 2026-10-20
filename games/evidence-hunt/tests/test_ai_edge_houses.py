"""Edge-case tests for houses.py."""

import houses as h


def test_rooms_of_smallest_layout():
    """rooms_of returns exactly 3 rooms for the smallest layout 'cottage'."""
    rooms = h.rooms_of("cottage")
    assert len(rooms) == 3
    assert all(isinstance(r, dict) for r in rooms)
    assert all(k in r for r in rooms for k in ("id", "type", "name", "floor", "col", "row", "text"))


def test_rooms_of_largest_layout():
    """rooms_of returns exactly 14 rooms for the largest layout 'grand'."""
    rooms = h.rooms_of("grand")
    assert len(rooms) == 14


def test_size_of_boundary_values():
    """size_of matches the number of rooms for the smallest and largest layouts."""
    assert h.size_of("cottage") == 3
    assert h.size_of("grand") == 14


def test_floors_of_empty_input():
    """floors_of returns an empty list when given no rooms."""
    assert h.floors_of([]) == []


def test_floors_of_negative_and_positive():
    """floors_of correctly sorts floors including negative cellar levels."""
    rooms = h.rooms_of("mill")
    floors = h.floors_of(rooms)
    assert -1 in floors
    assert 0 in floors
    assert 1 in floors
    assert 2 in floors
    assert floors == sorted(floors, reverse=True)


def test_floors_of_single_room():
    """floors_of returns a single-element list for one room."""
    rooms = h.rooms_of("cottage")[:1]
    assert h.floors_of(rooms) == [rooms[0]["floor"]]
