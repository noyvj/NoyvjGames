"""Edge-case tests for bench.py."""

import bench


def _make_bench(tray=None, solution=None, count=1, number=1):
    data = {
        "id": "c1-1",
        "name": "Test Bench",
        "rows": [">A"],
        "tray": tray or {},
        "solution": solution or [],
        "par": 0,
        "count": count,
        "line": "",
    }
    return bench.Bench(data, chapter=1, number=number)


def test_tray_size_with_empty_tray():
    b = _make_bench(tray={})
    assert b.tray_size == 0


def test_tray_size_with_zero_values():
    b = _make_bench(tray={"mirror": 0, "splitter": 0})
    assert b.tray_size == 0


def test_solution_layout_with_empty_solution():
    b = _make_bench(solution=[])
    assert b.solution_layout() == {}


def test_unique_property_when_count_is_one():
    b = _make_bench(count=1)
    assert b.unique is True


def test_unique_property_when_count_exceeds_one():
    b = _make_bench(count=5)
    assert b.unique is False


def test_number_stores_any_integer_without_clamping():
    # bench.py does not clamp or reject number; it stores whatever is passed.
    b_zero = _make_bench(number=0)
    assert b_zero.number == 0

    b_large = _make_bench(number=99)
    assert b_large.number == 99
